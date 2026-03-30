'''






'''


import datetime
import io
import os
import wave

import aiofiles
from dotenv import load_dotenv
from fastapi import WebSocket
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.azure.llm import AzureLLMService
from pipecat.services.azure.stt import AzureSTTService
from pipecat.services.azure.tts import AzureTTSService
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from prompt.call_one import get_prompt as get_prompt_one
from prompt.call_two import get_prompt as get_prompt_two

load_dotenv()


# This function asynchronously writes buffered audio frames to a local WAV file.
# It takes incoming audio bytes along with sample rate and channel information to 
# format and save the conversation recording on the server's disk with a timestamped filename.
async def save_audio(
    server_name: str, audio: bytes, sample_rate: int, num_channels: int
):
    if audio:
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y/%m/%d_%H:%M:%S")
        wav_name = f"{server_name}_recording_{timestamp}.wav"
        buffer = io.BytesIO()
        with wave.open(buffer, mode="wb") as wav_file:
            wav_file.setsampwidth(2)
            wav_file.setnchannels(num_channels)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio)
        buffer.seek(0)
        async with aiofiles.open(wav_name, mode="wb") as out_file:
            await out_file.write(buffer.read())
        print(f"Audio file saved at {wav_name}")
    else:
        print("No audio data to save")


# This function handles the core conversational AI pipeline for the active Twilio phone call.
# It sets up Speech-to-Text (STT), a Large Language Model (LLM), and Text-to-Speech (TTS) using Azure services,
# binds them to the WebSocket transport, generates a dynamic prompt based on the user's data payload, 
# and runs the Pipecat agent pipeline while handling events like call disconnection.
async def handle_voice_agent(
    websocket_client: WebSocket,
    stream_sid: str,
    call_sid: str,
    user_data: dict = None
):
    if user_data is None:
        user_data = {}
    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            serializer=TwilioFrameSerializer(stream_sid),
        ),
    )

    llm = AzureLLMService(
        api_key=os.getenv("AZURE_API_KEY"),
        model=os.getenv('AZURE_DEPLOYMENT'),
        api_version=os.getenv('AZURE_API_VERSION'),
        endpoint=os.getenv('AZURE_ENDPOINT'),
    )

    stt = AzureSTTService(
        api_key=os.getenv("AZURE_SPEECH_API_KEY"),
        region=os.getenv("AZURE_SPEECH_REGION"),
        language="en-US",
    )

    tts = AzureTTSService(
        api_key=os.getenv("AZURE_SPEECH_API_KEY"),
        region=os.getenv("AZURE_SPEECH_REGION"),
    )

    call_type = user_data.get("call_type")
    if call_type == 1:
        system_prompt = get_prompt_one(user_data)
    else:
        system_prompt = get_prompt_two(user_data)

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
    ]

    # 👇 THIS is the exact element that logs and tracks the entire conversation!
    # It starts with the initial system prompt, and continuously appends every 
    # new thing the User or the Agent says throughout the call.
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    audiobuffer = AudioBufferProcessor()

    pipeline = Pipeline(
        [
            transport.input(),  # Websocket input from client
            stt,  # Speech-To-Text
            context_aggregator.user(), # <-- Adds the user's spoken words to the context
            llm,  # LLM
            tts,  # Text-To-Speech
            transport.output(),  # Websocket output to client
            audiobuffer,  # Used to buffer the audio in the pipeline
            context_aggregator.assistant(), # <-- Adds the AI's spoken words to the context
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            allow_interruptions=True,
        ),
    )

    # 1. Defines when the client connects to the server
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        await audiobuffer.start_recording()
        messages.append(
            {"role": "system", "content": "Please introduce yourself to the user."}
        )
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    # 2. Defines when the audio data is being received from the client
    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        server_name = f"server_{websocket_client.client.port}"
        await save_audio(server_name, audio, sample_rate, num_channels)

    # 3. Defines when the client disconnects from the server
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await task.cancel()
        
        # Save transcript to Cosmos DB
        try:
            from db import save_transcript_to_cosmos
            # Fetch the completed conversation history from the context
            full_transcript = context.get_messages()
            # Send the call_sid (CA...) not the stream_sid (MZ...) to the database!
            await save_transcript_to_cosmos(call_sid, full_transcript, user_data)
        except Exception as e:
            print(f"⚠️ Error preparing transcript save: {e}")

    runner = PipelineRunner(handle_sigint=False, force_gc=True)
    await runner.run(task)

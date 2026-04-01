# # pip install webrtcvad
# # pip install webrtcvad pipecat-ai aiofiles python-dotenv fastapi

# # Remove
# # from pipecat.audio.vad.silero import SileroVADAnalyzer

# # Add
# # import webrtcvad
# # from pipecat.audio.vad.base import VADAnalyzer

# # This is needed 
# # webrtcvad==2.0.10

# # 2, 3 for faster interuption
# # aggressiveness=2

# # 2. If install fails (common on Windows/Mac)

# # Run:

# # pip install wheel setuptools pip --upgrade
# # pip install webrtcvad

# # If still failing:

# # pip install webrtcvad-wheels






# import datetime
# import io
# import os
# import wave

# import aiofiles
# from dotenv import load_dotenv
# from fastapi import WebSocket

# # ✅ CHANGED: Use WebRTC VAD instead of Silero
# from pipecat.audio.vad.webrtc import WebRTCVADAnalyzer

# from pipecat.pipeline.pipeline import Pipeline
# from pipecat.pipeline.runner import PipelineRunner
# from pipecat.pipeline.task import PipelineParams, PipelineTask
# from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
# from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
# from pipecat.serializers.twilio import TwilioFrameSerializer
# from pipecat.services.azure.llm import AzureLLMService
# from pipecat.services.azure.stt import AzureSTTService
# from pipecat.services.azure.tts import AzureTTSService
# from pipecat.transports.network.fastapi_websocket import (
#     FastAPIWebsocketParams,
#     FastAPIWebsocketTransport,
# )

# from prompt.call_one import get_prompt as get_prompt_one
# from prompt.call_two import get_prompt as get_prompt_two

# load_dotenv()


# async def save_audio(
#     server_name: str, audio: bytes, sample_rate: int, num_channels: int
# ):
#     if audio:
#         now = datetime.datetime.now()
#         timestamp = now.strftime("%Y/%m/%d_%H:%M:%S")
#         wav_name = f"{server_name}_recording_{timestamp}.wav"

#         buffer = io.BytesIO()
#         with wave.open(buffer, mode="wb") as wav_file:
#             wav_file.setsampwidth(2)
#             wav_file.setnchannels(num_channels)
#             wav_file.setframerate(sample_rate)
#             wav_file.writeframes(audio)

#         buffer.seek(0)

#         async with aiofiles.open(wav_name, mode="wb") as out_file:
#             await out_file.write(buffer.read())

#         print(f"Audio file saved at {wav_name}")
#     else:
#         print("No audio data to save")


# async def handle_voice_agent(
#     websocket_client: WebSocket,
#     stream_sid: str,
#     call_sid: str,
#     user_data: dict = None
# ):
#     if user_data is None:
#         user_data = {}

#     transport = FastAPIWebsocketTransport(
#         websocket=websocket_client,
#         params=FastAPIWebsocketParams(
#             audio_in_enabled=True,
#             audio_out_enabled=True,
#             add_wav_header=False,
#             vad_enabled=True,

#             # ✅ CHANGED: WebRTC VAD
#             vad_analyzer=WebRTCVADAnalyzer(
#                 aggressiveness=2  # tweak 0–3
#             ),

#             vad_audio_passthrough=True,
#             serializer=TwilioFrameSerializer(stream_sid),
#         ),
#     )

#     llm = AzureLLMService(
#         api_key=os.getenv("AZURE_API_KEY"),
#         model=os.getenv('AZURE_DEPLOYMENT'),
#         api_version=os.getenv('AZURE_API_VERSION'),
#         endpoint=os.getenv('AZURE_ENDPOINT'),
#     )

#     stt = AzureSTTService(
#         api_key=os.getenv("AZURE_SPEECH_API_KEY"),
#         region=os.getenv("AZURE_SPEECH_REGION"),
#         language="en-US",
#     )

#     tts = AzureTTSService(
#         api_key=os.getenv("AZURE_SPEECH_API_KEY"),
#         region=os.getenv("AZURE_SPEECH_REGION"),
#     )

#     call_type = user_data.get("call_type")

#     if call_type == 1:
#         system_prompt = get_prompt_one(user_data)
#     else:
#         system_prompt = get_prompt_two(user_data)

#     messages = [
#         {
#             "role": "system",
#             "content": system_prompt,
#         },
#     ]

#     context = OpenAILLMContext(messages)
#     context_aggregator = llm.create_context_aggregator(context)

#     audiobuffer = AudioBufferProcessor()

#     pipeline = Pipeline(
#         [
#             transport.input(),
#             stt,
#             context_aggregator.user(),
#             llm,
#             tts,
#             transport.output(),
#             audiobuffer,
#             context_aggregator.assistant(),
#         ]
#     )

#     task = PipelineTask(
#         pipeline,
#         params=PipelineParams(
#             audio_in_sample_rate=8000,
#             audio_out_sample_rate=8000,
#             allow_interruptions=True,
#         ),
#     )

#     @transport.event_handler("on_client_connected")
#     async def on_client_connected(transport, client):
#         await audiobuffer.start_recording()

#         messages.append(
#             {"role": "system", "content": "Please introduce yourself to the user."}
#         )

#         await task.queue_frames([context_aggregator.user().get_context_frame()])

#     @audiobuffer.event_handler("on_audio_data")
#     async def on_audio_data(buffer, audio, sample_rate, num_channels):
#         server_name = f"server_{websocket_client.client.port}"
#         await save_audio(server_name, audio, sample_rate, num_channels)

#     @transport.event_handler("on_client_disconnected")
#     async def on_client_disconnected(transport, client):
#         await task.cancel()

#         try:
#             from db import save_transcript_to_cosmos

#             full_transcript = context.get_messages()
#             await save_transcript_to_cosmos(call_sid, full_transcript, user_data)

#         except Exception as e:
#             print(f"⚠️ Error preparing transcript save: {e}")

#     runner = PipelineRunner(handle_sigint=False, force_gc=True)
#     await runner.run(task)
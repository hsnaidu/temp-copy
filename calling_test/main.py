'''


'''


import json
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
import os
from twilio.rest import Client
from pydantic import BaseModel
from typing import Dict, Any
from utils import handle_voice_agent

active_calls = {}

app = FastAPI(
    title="Pipecat Azure outbound call handler",
    description="Caller Agnet to make outbound calls",
    version="0.1.0",
    contact={
        "name": "Hari Prasad S : Collections",
        "url": "<Need to add the github>",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# This function acts as the initial webhook endpoint for Twilio when a call is answered.
# It generates and returns XML (TwiML) instructing Twilio to immediately connect the 
# call's audio stream to our WebSocket server for real-time conversation processing.
@app.post("/")
async def init_call():

    # Here, I need to replace with the container-app
    webhook_url = os.getenv("WEBHOOK_URL", "https://your-ngrok-url.ngrok-free.app")

    # Replace the wss:// protocol for the WebSocket URL if needed
    ws_url = webhook_url.replace("https://", "wss://").replace("http://", "ws://")
    
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}/ws" />
    </Connect>
</Response>"""
    
    return HTMLResponse(content=content, media_type="application/xml")


# This function exposes an endpoint to trigger an outbound Twilio call using the provided JSON payload.
# It extracts the destination phone number, initiating the call via the Twilio REST API,
# and temporarily saves the entire user data payload in memory to be used when the WebSocket connects.
@app.post("/call")
async def make_call(request: Dict[str, Any]):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    webhook_url = os.getenv("WEBHOOK_URL")

    client = Client(account_sid, auth_token)

    user_phone = request.get("user_phone")
    if not user_phone:
        return {"error": "user_phone is required"}

    call = client.calls.create(
        from_=from_number,
        to=user_phone,
        url=f"{webhook_url}/"
    )

    active_calls[call.sid] = request

    return {"status": "Call initiated", "call_sid": call.sid}


# This function handles the live, bidirectional WebSocket connection established by Twilio.
# It accepts the connection, receives the initial stream metadata (including Twilio's Call SID),
# looks up the user's JSON payload saved during call initiation, and triggers the voice agent.
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    init_data = websocket.iter_text()
    await init_data.__anext__()
    call_data = json.loads(await init_data.__anext__())
    print(call_data, flush=True)
    stream_sid = call_data["start"]["streamSid"]
    # Twilio sends both the Media Stream ID (MZ...) and the Call ID (CA...)
    call_sid = call_data["start"]["callSid"]
    
    print(f"WebSocket connected to the call: {stream_sid}")
    
    user_data = active_calls.get(call_sid, {})
    await handle_voice_agent(websocket, stream_sid, call_sid, user_data)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

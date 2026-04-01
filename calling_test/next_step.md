# Comprehensive System End-to-End Guide

This document explains the entire architecture of the calling platform in detail. It breaks down what every file does, how the JSON data flows through the system step-by-step, how to automate the trigger, and how to test it manually using Postman.

---

## 1. System Architecture: File by File Breakdown

Think of this application in three phases: **1. Initiating the Call**, **2. Processing the Live Conversation**, and **3. Post-Call Analytics & Display**. 

### Phase 1: Initiating the Call
**`main.py` (The Command Center & Web Server)**
This is the root file running your entire FastAPI server (`uvicorn main:app`). It listens for requests on Port 8000.
* **`@app.post("/call")`**: When you click a button on the frontend, it sends your massive JSON payload here. This function strips out the `user_phone`, uses the Twilio SDK to dial that number, and holds your JSON payload temporarily in the server's memory (`active_calls`).
* **`@app.post("/")` & `@app.websocket("/ws")`**: When Twilio connects the call, it hits these endpoints to stream the live audio securely back and forth between the phone call and your Pipecat bot.
* **The API Router**: At the very top, `main.py` also imports `api/main.py` so that your frontend text boxes can securely request data from this exact same server.

### Phase 2: Processing the Live Conversation
**`utils.py` (The Live AI Caller Engine)**
Once the WebSocket connects in `main.py`, it immediately hands control over to `utils.py`.
* **`handle_voice_agent()`**: This function builds the "Pipecat Pipeline". It connects Azure Speech-to-Text (to hear the user), the LLM (to think of replies based on your system prompts), and Text-to-Speech (to talk back).
* **The Live Memory `context`**: As the agent and the human talk, Pipecat continuously records every single sentence spoken into a memory variable called `context`.
* **`on_client_disconnected()`**: This is the magic trigger. The exact millisecond the user hangs up the phone, this function fires. It grabs the entire conversation history from `context.get_messages()`, injects it right back into your original JSON payload, and hands it off to your Postcall scripts.

### Phase 3: Post-Call Analytics & Display
**`postcall/main.py` (The Analytics Brain)**
Triggered by `utils.py` the moment the call ends. 
* **`process_transcript_and_update_json()`**: This function receives your JSON holding the transcript. It spins up an asynchronous LangChain Agent. It tells the Azure LLM: *"Read this transcript, and use your 3 tools to extract the data."* 
* Because it is asynchronous (`await process_transcript_and_update_json()`), the server doesn't freeze. If 40 calls end at the exact same time, 40 separate instances of this function run simultaneously in parallel.
* Once the LLM finishes, it glues the newly generated Action Items, Summary, and Categorization onto your JSON, and saves it permanently to the database (`result.txt` / Cosmos DB).

**`postcall/tools/` (The AI Blueprints)**
These three files (`summary.py`, `actionitems.py`, `categorization.py`) act as strict guardrails for the LangChain agent.
* Instead of the AI writing a messy paragraph, these files use Pydantic classes to force the AI to return data in the exact JSON format your frontend needs. 
* `categorization.py` literally disables the AI from writing anything other than `"pending"`, `"cleared"`, or `"dispute"`. `actionitems.py` forces the AI to output exactly two dictionary keys: `"user_action"` and `"agent_action_item"`. 

**`api/main.py` (The Frontend Delivery System)**
* This file contains 4 lightning-fast `GET` endpoints (`/api/users/{case_id}/summary`, etc.).
* Instead of sending your massive, heavy Cosmos DB JSON row back to the frontend, these endpoints act as precision snipers. They quickly scan the saved database for the exact `case_id`, grab *only* the tiny string required for that specific text box, and shoot it to the frontend.

---

## 2. The Data Flow (Start to Finish)

Here is exactly how the JSON transforms as it travels through the system.

### A. The Trigger Payload (Frontend to Backend)
This is the JSON your frontend sends securely to `/call` when you click the button.
```json
{
  "case_id": "201ABC", 
  "user_name": "David Miller",
  "user_phone": "+233-500-101",
  "due_date": "2022-02-01", 
  "user_mail": "david.miller@example.com",
  "collector_name": "agent",
  "collector_id": "123ABC",
  "billing_address": "Some address",
  "invoice_amount": "$1123.40",
  "short_payment": 1,
  "over_payment": 0,
  "call_type": 1,
  "dispute": "$123.00",
  "preferred_language": "English",
  "notes": ["NA"],
  "status": ["pending"],
  "invoice": ["INV001","INV002"],
  "total_invoice": 2,
  "agent_contanct": true,
  "audio_recording": true,
  "prefered_contact_time": "14:30 EST",
  "account_status": "active"
}
```

### B. Pre-Processing Payload (Backend to LangChain Agent)
The call is over. Your Pipecat bot successfully spoke to David. In `utils.py`, your backend injects the `transcript` into the payload, bringing the data entirely into memory before calling `postcall/main.py`.
```json
{
  "case_id": "201ABC", 
  ... // [All Original Fields stay exactly the same]
  "transcript": [
     {"role": "system", "content": "You are a collections agent..."},
     {"role": "assistant", "content": "Hello David, I am calling regarding your invoice..."},
     {"role": "user", "content": "Yes, I lost my job recently. I can only pay $500 right now."}
  ]
}
```

### C. Final Stored Output (Saved to DB & API output)
The LangChain agent processes the transcript using the 3 tools. It appends its intelligence back to the same JSON. This exact structure is saved into your Cosmos DB and `result.txt`.
```json
{
  "case_id": "201ABC",
  "user_name": "David Miller",
  "user_phone": "+233-500-101",
  "due_date": "2022-02-01",
  "user_mail": "david.miller@example.com",
  "collector_name": "agent",
  "collector_id": "123ABC",
  "billing_address": "Some address",
  "invoice_amount": "$1123.40",
  "short_payment": 1,
  "over_payment": 0,
  "call_type": 1,
  "dispute": "$123.00",
  "preferred_language": "English",
  "notes": ["NA"],
  "status": ["pending"],
  "invoice": ["INV001", "INV002"],
  "total_invoice": 2,
  "agent_contanct": true,
  "audio_recording": true,
  "prefered_contact_time": "14:30 EST",
  "account_status": "active",
  
  "transcript": [
     {"role": "assistant", "content": "Hello David..."},
     {"role": "user", "content": "I can only pay $500 today."}
  ],
  "action_items": {
     "user_action": "Log into the portal to process the $500 partial payment immediately.",
     "agent_action_item": "Call back David next week on Wednesday to collect the remaining balance."
  },
  "summary": "David Miller acknowledged the invoice but claimed financial hardship, agreeing to pay a partial amount of $500 today.",
  "categorization": "pending"
}
```

---

## 3. How Automation Works (Triggering without clicking a button)

If you want to automate this process for hundreds of users so no human intervention is needed:

**The CRON Job / Scheduled Task Method:**
You write a simple script that runs daily on your Azure infrastructure.
1. The script connects to your main database where your pending cases live.
2. It loops through all `case_id`s that have `status: "pending"` and whose `due_date` has passed.
3. For every user, it automatically fires the identical `POST` request to `https://<YOUR-APP-URL>/call`. 
4. Because the FastAPI web server natively handles concurrency asynchronously, you can loop through 40 users in 1 second, and the system will launch 40 simultaneous Twilio calls flawlessly.

---

## 4. Postman Testing Guide

To test the entire life cycle for a single call manually using Postman:

### Step 1: Initiate the Call
1. Open Postman, select **POST**.
2. URL: `http://localhost:8000/call` (or your Azure Container App URL).
3. Under the **Body** tab, select **raw** and format as **JSON**.
4. Paste your exact JSON block (from section 2.A above).
5. Click **Send**.
*(Expected result: Status 200 OK. Your phone will instantly ring.)*

### Step 2: Simulate the Conversation
1. Pick up the phone.
2. Speak to the Pipecat agent. (For testing the "dispute" categorization, try acting angry: "I refuse to pay this invoice because the service was terrible!").
3. Hang up the phone. 

### Step 3: View the Postcall Output via APIs!
Wait about 5 to 10 seconds for the asynchronous LangChain agent to finish evaluating the argument you just had with the bot.

**Check Summary:**
- **GET** `http://localhost:8000/api/users/201ABC/summary`
- *Expected response:* `{"summary": "David aggressively refused to pay the remaining invoice citing poor service quality."}`

**Check Categorization:**
- **GET** `http://localhost:8000/api/users/201ABC/categorization`
- *Expected response:* `{"categorization": "dispute"}`

**Check Action Items:**
- **GET** `http://localhost:8000/api/users/201ABC/action_items`
- *Expected response:*
  ```json
  {
    "action_items": {
      "user_action": "None",
      "agent_action_item": "Escalate account 201ABC to a human manager for dispute resolution regarding service quality."
    }
  }
  ```

---

## 5. Deployment Checklist (Files to Push)

When you are ready to push your pipeline to Azure Container Apps, ensure you commit the following modified/new files into your repository:

1. **`requirements.txt`**: Added `langchain`, `langchain-openai`, and `langchain-core` so the container doesn't crash on boot.
2. **`main.py` (Root)**: Updated to import and mount the `api/main.py` router so the single container serves both webhooks and the React APIs.
3. **`utils.py`**: Updated to capture the live transcript from Pipecat's memory and trigger the asynchronous postcall script when the user disconnects.
4. **`postcall/` folder**: Contains `main.py` (The LangChain Agent) and the `tools/` directory (The Pydantic bluepints).
5. **`api/` folder**: Contains `main.py` which exposes the 4 specific `GET` endpoints for your frontend.

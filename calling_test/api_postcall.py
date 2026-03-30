import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from azure.cosmos import CosmosClient
import uvicorn
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Post-Call Frontend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# COSMOS DB SETUP
# ---------------------------------------------------------
ENDPOINT = os.getenv("ENDPOINT")
KEY = os.getenv("KEY")
DATABASE_NAME = os.getenv("DATABASE_NAME", "user-data")
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "user-statements")

# Attempt to initialize client once on startup securely
try:
    client = CosmosClient(ENDPOINT, credential=KEY)
    db = client.get_database_client(DATABASE_NAME)
    container = db.get_container_client(CONTAINER_NAME)
except Exception as e:
    print(f"Failed to connect to Cosmos DB: {e}")
    container = None

# ---------------------------------------------------------
# API ENDPOINT FOR FRONTEND
# ---------------------------------------------------------

@app.get("/api/summary/{call_sid}")
async def get_summary(call_sid: str):
    """
    Fetches only the latest summary note for the given call.
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    try:
        item = container.read_item(item=call_sid, partition_key=call_sid)
        return {
            "call_sid": call_sid,
            "latest_summary_note": item.get("notes", [""])[-1] if item.get("notes") else None,
            "all_notes_history": item.get("notes", [])
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Call record not found: {str(e)}")

@app.get("/api/action-items/{call_sid}")
async def get_action_items(call_sid: str):
    """
    Fetches only the action items for the given call.
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    try:
        item = container.read_item(item=call_sid, partition_key=call_sid)
        return {
            "call_sid": call_sid,
            "action_items": item.get("action_items", {})
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Call record not found: {str(e)}")

@app.get("/api/categorization/{call_sid}")
async def get_categorization(call_sid: str):
    """
    Fetches only the categorization (status) logic for the given call.
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    try:
        item = container.read_item(item=call_sid, partition_key=call_sid)
        return {
            "call_sid": call_sid,
            "latest_categorization_status": item.get("status", [""])[-1] if item.get("status") else None,
            "all_status_history": item.get("status", [])
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Call record not found: {str(e)}")

if __name__ == "__main__":
    # Start the API on port 8002 to avoid conflict with other apps
    uvicorn.run(app, host="0.0.0.0", port=8002)

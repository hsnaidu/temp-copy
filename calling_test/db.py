'''




'''







import os
from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError
from dotenv import load_dotenv
from twilio.rest import Client
import datetime
import json

load_dotenv()

COSMOS_ENDPOINT = os.getenv("ENDPOINT")
COSMOS_KEY = os.getenv("KEY")
DATABASE_NAME = os.getenv("DATABASE_NAME", "user-data")
CONTAINER_NAME = os.getenv("CONTAINER_NAME", "user-statements")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# This function retrieves live call metadata from Twilio and saves it alongside the conversation transcript.
# It bundles the Twilio data, the full chat history, and the user's entire original JSON payload 
# into a single comprehensive document and upserts it into the pre-configured Azure Cosmos DB container.
async def save_transcript_to_cosmos(call_sid: str, transcript: list, user_data: dict = None):
    if user_data is None:
        user_data = {}
    """
    Saves the full Pipecat conversation transcript alongside Twilio Call metadata to Azure Cosmos DB.
    """
    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        print("⚠️ Cosmos DB Endpoint or Key not found in .env. Skipping transcript save.")
        return

    # 1. Fetch live call details from Twilio using the SID
    call_metadata = {}
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        try:
            twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            call_details = twilio_client.calls(call_sid).fetch()
            
            # Extract whatever metadata you want!
            call_metadata = {
                "status": call_details.status,
                "duration_seconds": call_details.duration,
                "direction": call_details.direction,
                "from_number": call_details.from_,
                "to_number": call_details.to,
                "price": str(call_details.price) if call_details.price else "0",
                "price_unit": call_details.price_unit
            }
        except Exception as e:
            print(f"⚠️ Could not fetch Twilio call details: {e}")

    # 2. Upload everything together to Cosmos DB
    try:
        # Initialize async Cosmos client
        async with CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY) as client:
            db = client.get_database_client(DATABASE_NAME)
            container = db.get_container_client(CONTAINER_NAME)
            
            # Prepare the JSON document
            document = user_data.copy()
            document.update({
                "id": call_sid,
                "user_id": call_sid,  # Using call_sid as the partition key for this transcript
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "twilio_metadata": call_metadata,
                "transcript": transcript
            })
            
            # Upsert (create or update) the transcript document
            await container.upsert_item(document)
            print(f"✅ Successfully saved transcript and metadata for call {call_sid} to Cosmos!")
            
    except CosmosHttpResponseError as e:
        print(f"❌ Failed to save transcript to Cosmos DB. Error: {e.message}")
    except Exception as e:
        print(f"❌ Unexpected Error saving to Cosmos: {e}")

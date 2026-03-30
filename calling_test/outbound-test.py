import os
import requests
import json
import time
from dotenv import load_dotenv
from twilio.rest import Client


load_dotenv(".env")

# WEBHOOK_URL = "http://localhost:8000/"

WEBHOOK_URL = "https://collections-generic-pipekat-demo.greenbush-e655dfbf.westeurope.azurecontainerapps.io"

if not WEBHOOK_URL:
    print("Error: WEBHOOK_URL not found in app/.env. Please add it first.")
    exit(1)

# Ensure the webhook URL doesn't have a trailing slash before adding /call
URL = f"{WEBHOOK_URL.rstrip('/')}/call"

# Change the number -> Twilio verified 

DESTINATION_PHONE_NUMBER = "+919900371904"

payloads = [
    {
        "case_id": "201ABC",
        "user_name": "David Miller",
        "user_phone": DESTINATION_PHONE_NUMBER,
        "due_date": "2022-02-01",
        "invoice_amount": "$1123.40",
        "call_type": 1,
        "notes": ["NA"],
    },
    {
        "case_id": "305XYZ",
        "user_name": "Sarah Connor",
        "user_phone": DESTINATION_PHONE_NUMBER,
        "due_date": "2023-05-15",
        "invoice_amount": "$450.00",
        "call_type": 2,
        "notes": ["Requires immediate follow up"],
    }
]

headers = {
    'Content-Type': 'application/json'
}

# This function requests detailed diagnostic data about a specific call directly from Twilio.
# It uses the Twilio SDK to fetch the call details corresponding to the provided Call SID,
# dynamically extracts all available public attributes from the response object, and returns them as a JSON string.
def get_call_details(call_sid):
    """Fetches call details from Twilio and returns the full JSON object."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("⚠️  Warning: TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not found in .env, cannot fetch call details.")
        return None
        
    client = Client(account_sid, auth_token)
    
    try:
        call = client.calls(call_sid).fetch()
        call_dict = {}
        for key in dir(call):
            if not key.startswith('_') and not callable(getattr(call, key)):
                call_dict[key] = getattr(call, key)
        
        call_json = json.dumps(call_dict, default=str, indent=2)
        return call_json
    except Exception as e:
        print(f"❌ Error fetching call details from Twilio: {e}")
        return None

for i, payload_dict in enumerate(payloads):
    print(f"\n--- Testing Payload {i+1} (Call Type {payload_dict['call_type']}) ---")
    print(f"Triggering outbound call from agent to {DESTINATION_PHONE_NUMBER}...\n")
    
    payload = json.dumps(payload_dict)

    try:
        response = requests.post(URL, headers=headers, data=payload)
        
        if response.status_code == 200:
            print("Call initiated successfully!")
            result = response.json()
            print("Server Response:")
            print(json.dumps(result, indent=2))
            print("\nYour phone should be ringing within a few seconds!")
            
            call_sid = result.get("call_sid")
            if call_sid:
                print("Waiting 3 seconds for Twilio to connect the call before fetching details...")
                time.sleep(3)
                
                full_call_json = get_call_details(call_sid)
                if full_call_json:
                    print("Full Twilio Call JSON Data:")
                    # Truncating print just so the terminal isn't completely flooded
                    print(full_call_json[:500] + "...\n")
                    
        else:
            print(f"Failed to initiate call (Status Code {response.status_code}):")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to the endpoint: {e}")
        print("Ensure that your FastAPI server is running and the URL is correct.")
        
    print(f"--- Finished Payload {i+1} ---\n")
    time.sleep(5) # Wait a bit before triggering the next payload


# Knwoledge Cut-off is October 2023'
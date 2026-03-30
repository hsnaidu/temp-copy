import os
import requests
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="React Intermediary Backend")

# Allow your React app to send requests without CORS errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, change this to your React app's URL (e.g. "http://localhost:3000")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# This is the URL of your deployed Pipecat voice container
# Update this to point to the actual endpoint where your Pipecat code is running
CONTAINER_APP_URL = os.getenv("CONTAINER_APP_URL", "https://collections-generic-pipekat-demo.greenbush-e655dfbf.westeurope.azurecontainerapps.io/call")

@app.post("/trigger-call")
async def trigger_call_from_react(payload: Dict[str, Any]):
    """
    When you click a button in your React app's row, it will send the row's JSON data to this endpoint.
    This function takes that JSON and forwards it to your voice agent container to initiate the call.
    """
    print(f"Received request from React to call: {payload.get('user_phone')}")
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        # Forward the same payload to your voice container
        response = requests.post(CONTAINER_APP_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            return {"status": "success", "message": "Call initiated successfully", "data": response.json()}
        else:
            return {"status": "error", "message": "Failed to trigger call in container", "details": response.text}
            
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Run this backend server on port 8001 so it doesn't conflict with your Pipecat app (which runs on 8000)
    uvicorn.run(app, host="0.0.0.0", port=8001)






























# // Add this function to your React component
# const handleCallUser = async (rowData) => {
#   try {
#     // We send the row's data to our local python backend running on port 8001
#     const response = await fetch('http://localhost:8001/trigger-call', {
#       method: 'POST',
#       headers: {
#         'Content-Type': 'application/json',
#       },
#       // Pass the specific row's JSON data
#       body: JSON.stringify(rowData) 
#     });
#     const result = await response.json();
    
#     if (result.status === "success") {
#       alert(`Calling ${rowData.user_name} at ${rowData.user_phone}...`);
#     } else {
#       alert("Failed to initiate call.");
#       console.error(result);
#     }
#   } catch (error) {
#     console.error("Error communicating with local backend:", error);
#   }
# };
# // ... inside your render method, where you render each row:
# return (
#   <tr>
#     <td>{rowData.user_name}</td>
#     <td>{rowData.user_phone}</td>
#     <td>{rowData.invoice_amount}</td>
#     <td>
#       {/* Pass the data for this specific row when clicked */}
#       <button onClick={() => handleCallUser(rowData)}>
#         Initiate Call
#       </button>
#     </td>
#   </tr>
# );
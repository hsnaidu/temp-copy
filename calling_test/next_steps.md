# Next Steps & Integration Guide

This document outlines exactly how to integrate the backend with your React frontend, and how to test the entire flow using Postman.

## 1. How to Test End-to-End in Postman

Before touching the frontend code, you can simulate everything using Postman:

**Step A: Simulate the "Button Click" to Trigger the Call**
1. Open Postman.
2. Method: **POST**
3. URL: `https://collections-generic-pipekat-demo.greenbush-e655dfbf.westeurope.azurecontainerapps.io/call` (or your local `http://localhost:8000/call`)
4. Go to the **Body** tab, select **raw**, and choose **JSON**.
5. Paste your JSON payload:
   ```json
   {
     "case_id": "201ABC",
     "user_name": "David Miller",
     "user_phone": "+919900371904",
     "call_type": 1,
     "invoice_amount": "$1123.40"
     // ... rest of your fields
   }
   ```
6. Click **Send**. Your phone will ring! Answer it, have a quick conversation, and hang up.

**Step B: Simulate the Frontend "Polling"**
1. Wait about 10–15 seconds after hanging up to give the LLM time to generate the summary.
2. Open a *New Request* in Postman.
3. Method: **GET**
4. URL: `https://collections-generic-pipekat-demo.greenbush-e655dfbf.westeurope.azurecontainerapps.io/api/users/201ABC/summary`
5. Click **Send**. 
6. You should see `{"summary": "..."}` returned! (If it returns 404, wait another 5 seconds and click Send again).

---

## 2. React Code: Sending the Data on Button Click

Here is the code to attach to your frontend button to trigger the call. It takes your row's JSON data and sends it to the container URL.

```jsx
import React from 'react';

const CallTriggerButton = ({ rowData }) => {
  const handleTriggerCall = async () => {
    try {
      // 1. Send the huge JSON payload to the Azure Container
      const response = await fetch("https://collections-generic-pipekat-demo.greenbush-e655dfbf.westeurope.azurecontainerapps.io/call", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(rowData), // rowData contains case_id, user_phone, etc.
      });

      if (response.ok) {
        alert("Call initiated successfully!");
      } else {
        alert("Failed to initiate call.");
      }
    } catch (error) {
      console.error("API Error:", error);
    }
  };

  return (
    <button onClick={handleTriggerCall} className="bg-blue-600 text-white px-4 py-2 rounded">
      Call {rowData.user_name}
    </button>
  );
};
```

---

## 3. React Code: Polling the API Every 3 Seconds

This component handles the 4 API text boxes. It automatically fetches the data every 3 seconds until it stops getting a 404 error (meaning the agent has finished processing the call).

```jsx
import React, { useState, useEffect } from 'react';

const PostcallDataViewer = ({ caseId }) => {
  const [data, setData] = useState(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    // If we already have the data, stop fetching!
    if (!isProcessing) return;

    // Define the polling function
    const fetchPostcallData = async () => {
      try {
        const baseUrl = "https://collections-generic-pipekat-demo.greenbush-e655dfbf.westeurope.azurecontainerapps.io/api/users";
        
        // Fetch all 4 APIs simultaneously 
        const [summaryRes, transcriptRes, actionItemsRes, catRes] = await Promise.all([
          fetch(`${baseUrl}/${caseId}/summary`),
          fetch(`${baseUrl}/${caseId}/transcript`),
          fetch(`${baseUrl}/${caseId}/action_items`),
          fetch(`${baseUrl}/${caseId}/categorization`)
        ]);

        // If even one request succeeds (status 200), it means the LLM finished writing to the DB
        if (summaryRes.ok && transcriptRes.ok) {
          const summaryJson = await summaryRes.json();
          const transcriptJson = await transcriptRes.json();
          const actionJson = await actionItemsRes.json();
          const catJson = await catRes.json();

          // Save to state
          setData({
            summary: summaryJson.summary,
            transcript: transcriptJson.transcript,
            action_items: actionJson.action_items,
            categorization: catJson.categorization
          });

          // Stop the 3-second polling loop
          setIsProcessing(false); 
        }
      } catch (err) {
        console.log("Still waiting for agent to finish processing...", err);
      }
    };

    // Run the fetch function every 3000ms (3 seconds)
    const interval = setInterval(fetchPostcallData, 3000);

    // Cleanup the interval if the user leaves the page
    return () => clearInterval(interval);

  }, [caseId, isProcessing]);

  // Handle the UI while waiting for the API to return a 200 Success
  if (isProcessing) {
    return (
      <div className="p-4 border border-gray-200 mt-2 bg-gray-50 text-gray-500 animate-pulse">
        <p>Call finished. AI Agent currently analyzing transcript... ⏳</p>
      </div>
    );
  }

  // Once data arrives, display the 4 text boxes
  return (
    <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
      <div className="border p-2">
        <h4 className="font-bold">Transcript</h4>
        <p>{data.transcript}</p>
      </div>
      <div className="border p-2">
        <h4 className="font-bold">Summary</h4>
        <p>{data.summary}</p>
      </div>
      <div className="border p-2">
        <h4 className="font-bold">Categorization</h4>
        <p>{data.categorization}</p>
      </div>
      <div className="border p-2">
        <h4 className="font-bold">Action Items</h4>
        <ul className="list-disc ml-4">
          {data.action_items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default PostcallDataViewer;
```

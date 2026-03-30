import React, { useState } from 'react';

/**
 * This is an example React component representing a single row in your data table.
 * It handles:
 * 1. Sending the entire JSON payload to trigger the Pipecat voice call.
 * 2. Receiving the Twist Call SID.
 * 3. Polling the 3 separate Post-Call API endpoints after the call ends.
 * 4. Displaying the Summary, Categorization, and Action Items right below the row data.
 */
const UserTableRow = ({ rowData }) => {
  const [callStatus, setCallStatus] = useState("idle"); // idle, calling, fetching-results, completed
  const [callSid, setCallSid] = useState(null);

  // State for the Post-Call Agent Results
  const [summary, setSummary] = useState(null);
  const [actionItems, setActionItems] = useState(null);
  const [categorization, setCategorization] = useState(null);

  // 1. Trigger the Call
  const handleInitiateCall = async () => {
    setCallStatus("calling");
    try {
      // Send the entire specific row JSON to your local middleware (react_backend.py)
      const response = await fetch("http://localhost:8001/trigger-call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(rowData)
      });
      const result = await response.json();

      if (result.status === "success") {
        // We capture the unique twilio Call SID for this specific row!
        const sid = result.data.call_sid;
        setCallSid(sid);

        // Wait for the call to finish (Example: wait 30-60 secs, or add a manual "Fetch Results" button)
        // Here we simulate waiting 45 seconds before automatically polling Cosmos DB
        setTimeout(() => fetchPostCallResults(sid), 45000);
        setCallStatus("fetching-results");
      } else {
        setCallStatus("error");
      }
    } catch (error) {
      console.error(error);
      setCallStatus("error");
    }
  };

  // 2. Fetch the 3 different LLM results from api_postcall.py
  const fetchPostCallResults = async (sid) => {
    try {
      // Poll endpoint 1: Summary
      const resSummary = await fetch(`http://localhost:8002/api/summary/${sid}`);
      if (resSummary.ok) {
        const data = await resSummary.json();
        setSummary(data.latest_summary_note);
      }

      // Poll endpoint 2: Categorization (Status)
      const resCategory = await fetch(`http://localhost:8002/api/categorization/${sid}`);
      if (resCategory.ok) {
        const data = await resCategory.json();
        setCategorization(data.latest_categorization_status);
      }

      // Poll endpoint 3: Action Items
      const resActions = await fetch(`http://localhost:8002/api/action-items/${sid}`);
      if (resActions.ok) {
        const data = await resActions.json();
        setActionItems(data.action_items);
      }

      setCallStatus("completed");
    } catch (error) {
      console.error("Error fetching post-call data", error);
    }
  };

  return (
    <>
      <tr style={{ borderBottom: "1px solid #ccc" }}>
        <td>{rowData.case_id}</td>
        <td>{rowData.user_name}</td>
        <td>{rowData.user_phone}</td>
        <td>{rowData.invoice_amount}</td>

        <td>
          {callStatus === "idle" && (
            <button onClick={handleInitiateCall}>Initiate Call</button>
          )}
          {callStatus === "calling" && <span>📞 Calling...</span>}
          {callStatus === "fetching-results" && (
            <button onClick={() => fetchPostCallResults(callSid)}>Wait, or Click to Refresh Results</button>
          )}
          {callStatus === "completed" && <span style={{ color: "green" }}>✅ Call Analyzed</span>}
        </td>
      </tr>

      {/* REVEAL THE POST-CALL CONTAINERS IF DATA EXISTS */}
      {callStatus === "completed" && (
        <tr>
          <td colSpan="5" style={{ backgroundColor: "#f9f9f9", padding: "10px" }}>
            <div style={{ display: "flex", gap: "20px" }}>

              {/* Container 1: Summary */}
              <div style={{ flex: 1, border: "1px solid #ddd", padding: "10px" }}>
                <h4>📝 Call Summary</h4>
                <p>{summary || "No summary generated."}</p>
              </div>

              {/* Container 2: Categorization */}
              <div style={{ flex: 1, border: "1px solid #ddd", padding: "10px" }}>
                <h4>🏷️ Categorization</h4>
                <p><strong>{categorization || "Uncategorized"}</strong></p>
              </div>

              {/* Container 3: Action Items */}
              <div style={{ flex: 1, border: "1px solid #ddd", padding: "10px" }}>
                <h4>✅ Action Items</h4>
                {actionItems ? (
                  <ul>
                    <li><b>User Action:</b> {actionItems.user_action}</li>
                    <li><b>Agent Action:</b> {actionItems.agent_action_item}</li>
                  </ul>
                ) : (
                  <p>No action items found.</p>
                )}
              </div>

            </div>
          </td>
        </tr>
      )}
    </>
  );
};

export default UserTableRow;










// Since you mentioned earlier: "I have a react application in that i have user data in each row", you just need to:

// Paste the 

// react_example.jsx
//  file into your existing React project's src folder.
// Import it into your main table file (import UserTableRow from './react_example').
// Replace your current <tr> table rows with <UserTableRow rowData={actualJsonData} />.
// Run your React app normally (e.g., npm start or npm run dev) and you'll see it work instantly!
// If you want to test it in a brand-new visually working app right now from scratch, let me know and I can quickly run the commands to generate a basic Vite React App for you that renders it!
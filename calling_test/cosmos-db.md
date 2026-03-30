# Cosmos DB Architecture & Workflow Guide

Based on the requirements outlined in `NOTES.md`, here is the recommended structure and workflow for your Azure Cosmos DB.

## 1. How Many Tables (Containers) Do You Need?
You only need **ONE** table (in Cosmos DB, tables are called "Containers"). 

Cosmos DB is a NoSQL document database. Because your post-call agent simply augments the exact same data payload with new insights (summary, categories, action items), separating this into multiple SQL-style tables would create unnecessary complexity. A single evolving JSON document is the perfect NoSQL pattern.

## 2. Recommended Database Structure
- **Database Name:** `CollectionsDB` (or `user-data` as defined in your code)
- **Container Name:** `call_records` (or `user-statements`)
- **Partition Key:** `/case_id` or `/user_phone`
  *(Setting the Partition Key to `/case_id` or `/user_phone` allows you to quickly query all historical calls and notes for a specific case/user without scanning the whole database).*

## 3. Step-by-Step Data Flow

### Step A: The Caller Agent (Initial Insert)
1. The Pipecat agent triggers the call using the initial JSON.
2. When the call ends, your `db.py` script gathers the original JSON, the `twilio_metadata`, and the `transcript`.
3. It performs an **Upsert** (Insert or Update) into the Cosmos DB container.
4. The document now exists in the database with the raw transcript.

### Step B: The Post-Call Agent (Augmentation)
1. Your Post-Call Agent triggers (either via a Cosmos DB Change Feed trigger, or manually).
2. It **reads** the document from the Cosmos DB container.
3. It passes the `transcript` to your LLM tool to generate the summary, categorization, and action items.
4. The post-call agent **modifies the document in memory**:
   - Appends the summary to the `notes` array: `notes.append(summary)`
   - Appends the category to the `status` array: `status.append(categorization)`
   - Adds a brand new JSON object for `action_items`:
     ```json
     "action_items" : {
         "user_action": "User promised to pay by Friday",
         "agent_action_item" : "Follow up next Monday"
     }
     ```
5. It performs an **Upsert / Replace** operation back to Cosmos DB using the same document `id` and partition key.
6. The document is now fully enriched and your frontend/table can display the notes, status, and action items instantly.

## 4. Key Advantages of this Approach
- **No Joins Required:** Your React table frontend can fetch a single document and instantly have the user details, transcript, and AI action items all in one place.
- **Cost Effective:** Reading and writing to a single document costs fewer Request Units (RUs) than querying across multiple containers.
- **Easy History Tracking:** Since `notes` and `status` are arrays, appending to them creates a chronological history for that specific `case_id`.

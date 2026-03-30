'''
@mock_rawdata.json : 
    - Data we will be getting from the WEBCOLLECT
    - RAW Data 
    - This data is a sample data we extracted from the OD Screenshot

    {
        `Raw Data`-> This data will be extracted from the webcollect and sent to caller-agent may be there will be additional data with this but as of now lets stick to this data only :
        {
        "case_id": "201ABC", 
        "user_name": "David Miller",
        "user_phone": "+233-500-101",
        "due_date" : "2022-02-01", 
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
        "status" : ["pending"],
        "invoice" : ["INV001","INV002"],
        "total_invoice" : 2,
        "agent_contanct" : true,
        "transcript" : true,
        "audio_recording" : true,
        "prefered_contact_time" : <Take the regional time>,
        "account_status" : active
        },

        'From this data in the caller agent will mainly focus on the phone_number, call_type, notes, and the status, lets try to add a validation here -> Since the data we will get will be correct high changes it will go wrong since we are not extracting or anything sort of it..'
        ' Based on the type of the call we need to modify how the data wil flow, lets say for the second call are we considering the history if yes how many call history are we considering as of now it will be 1'
        ' So the caller agent will basically focus on the user_phone -> To make the call 
        'if notes == 'NA' and call_type == 1 use the prompt_one else use the prompt_two
        ' The pormpt_one will recive all the data to the prompt '
        'When the call goes it will have the user details in the prompt'


        `Data we are expecting to be in the after the call ends'
        {
        "case_id": "201ABC", // Replaced this with the case-id
        "user_name": "David Miller",
        "user_phone": "+233-500-101",
        "due_date" : "2022-02-01", 
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
        "status" : ["pending"],
        "invoice" : ["INV001","INV002"],
        "total_invoice" : 2,
        "agent_contanct" : true,
        "transcript" : true,
        "audio_recording" : true,
        "prefered_contact_time" : <Take the regional time>,
        "account_status" : active,
        "transcript" : {
            <user and the agent conversation>
        }
        },
        

        ' The post call agent will basically' take the transcipt from this conversation and then '
        ' Create the summarization and action items and categorization and write back to the same table so once its written it will display the sumamrization, categorization and the action items in the table,
        "sumamry will be updated back the the notes, categorization will be submitted back to the status list and then the action_items will be submitted back to the same table


        "case_id": "201ABC", // Replaced this with the case-id
        "user_name": "David Miller",
        "user_phone": "+233-500-101",
        "due_date" : "2022-02-01", 
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
        "status" : ["pending"],
        "invoice" : ["INV001","INV002"],
        "total_invoice" : 2,
        "agent_contanct" : true,
        "transcript" : true,
        "audio_recording" : true,
        "prefered_contact_time" : <Take the regional time>,
        "account_status" : active,
        "transcript" : {
            <user and the agent conversation>
        }
        "action_items" : {
            "user_action":<user_action_item>,
            "agent_action_item" : <agent_item>
        }
        },

    }















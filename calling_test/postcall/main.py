import os
import json
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from tools.summary import SaveSummary
from tools.actionitems import SaveActionItems
from tools.categorization import SaveCategorization

load_dotenv()

async def process_transcript_and_update_json(call_data: dict):
    """
    Takes the JSON call data, uses Langchain + Azure OpenAI to extract summary, 
    action items, and categorization from the transcript, appends them back, 
    and writes to a .txt file.
    """
    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
        api_version=os.getenv("OPENAI_API_VERSION", "2023-05-15"),
        temperature=0,
    )
    
    # State dictionary to hold the outputs from the tools
    extracted_state = {}

    @tool(args_schema=SaveSummary)
    def save_summary_tool(summary: str):
        """Use this tool to save the concise summary of the transcript."""
        extracted_state['summary'] = summary
        return "Summary saved."
        
    @tool(args_schema=SaveActionItems)
    def save_action_items_tool(user_action: str, agent_action_item: str):
        """Use this tool to save the extracted action items from the transcript."""
        # Save exact dict structure user requested
        extracted_state['action_items'] = {
            "user_action": user_action,
            "agent_action_item": agent_action_item
        }
        return "Action items saved."
        
    @tool(args_schema=SaveCategorization)
    def save_categorization_tool(category: str):
        """Use this tool to save the categorization of the call."""
        extracted_state['categorization'] = category
        return "Categorization saved."
        
    tools = [save_summary_tool, save_action_items_tool, save_categorization_tool]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an AI assistant processing post-call data. Analyze the transcript and MUST call all three tools provided (save_summary_tool, save_action_items_tool, save_categorization_tool) to extract and save the information."),
        ("human", "User: {user_name}\nTranscript:\n{transcript}")
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    # Process transcript which might be a dictionary or a string
    transcript = call_data.get("transcript", "")
    if isinstance(transcript, dict):
        transcript = json.dumps(transcript)
        
    # Execute the agent ASYNCHRONOUSLY
    await agent_executor.ainvoke({
        "user_name": call_data.get("user_name", "Unknown"),
        "transcript": transcript
    })
    
    # Append the results back to the original dictionary
    call_data['summary'] = extracted_state.get('summary', "No summary provided.")
    call_data['action_items'] = extracted_state.get('action_items', {"user_action": "", "agent_action_item": ""})
    call_data['categorization'] = extracted_state.get('categorization', "Unknown")
    
    # Write to a .txt file (as requested for now before cosmos DB integration)
    output_path = os.path.join(os.path.dirname(__file__), 'result.txt')
    
    # To keep a record of all users, we'll maintain a list in result.txt
    all_data = []
    if os.path.exists(output_path):
        with open(output_path, 'r') as f:
            try:
                all_data = json.load(f)
            except:
                pass
                
    # Update if exists, else append
    updated = False
    for i, data in enumerate(all_data):
        if data.get('case_id') == call_data.get('case_id'):
            all_data[i] = call_data
            updated = True
            break
            
    if not updated:
        all_data.append(call_data)
        
    with open(output_path, 'w') as f:
        json.dump(all_data, f, indent=4)
        
    return call_data

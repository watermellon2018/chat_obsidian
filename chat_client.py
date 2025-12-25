import os
import json
import httpx
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4.1-mini" # Using a capable model for tool-calling

# Import prompts
from prompts import SYSTEM_PROMPT, DEVELOPER_PROMPT, TOOL_POLICY

# --- MCP Tool Definitions (for LLM) ---

# Pydantic models for tool function signatures
class ListVaultFiles(BaseModel):
    """Lists all markdown file paths in the vault, relative to the vault root."""
    path: Optional[str] = Field(None, description="Optional subdirectory path to list files from.")

class SearchVault(BaseModel):
    """Searches for content or tags across all notes."""
    query: str = Field(..., description="Text or tag to search for.")
    search_type: str = Field("content", description="Type of search: 'content' or 'tag'.")

class ReadFileContent(BaseModel):
    """Reads the full content of a specific file."""
    path: str = Field(..., description="Relative path to the file in the vault.")

class GetFileMetadata(BaseModel):
    """Retrieves file metadata, including tags."""
    path: str = Field(..., description="Relative path to the file in the vault.")

# Map of tool names to their Pydantic schemas
TOOL_SCHEMAS = {
    "list_vault_files": ListVaultFiles,
    "search_vault": SearchVault,
    "read_file_content": ReadFileContent,
    "get_file_metadata": GetFileMetadata,
}

# --- Tool Call Handlers ---

async def call_mcp_tool(tool_call) -> str:
    """
    Handles a single tool call by making an HTTP request to the local MCP server.
    """
    tool_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    
    # Map tool name to FastAPI endpoint
    endpoint_map = {
        "list_vault_files": "/api/v1/files",
        "search_vault": "/api/v1/search",
        "read_file_content": "/api/v1/read",
        "get_file_metadata": "/api/v1/metadata",
    }
    
    endpoint = endpoint_map.get(tool_name)
    if not endpoint:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    url = f"{MCP_SERVER_URL}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            # Use GET for all defined MCP endpoints
            response = await http_client.get(url, params=arguments)
            response.raise_for_status()
            
            # Special handling for read_file_content to return just the content string
            if tool_name == "read_file_content":
                return response.json().get("content", "")
            
            return json.dumps(response.json())
            
    except httpx.HTTPStatusError as e:
        # Return a structured error for the LLM to process
        return json.dumps({"error": f"HTTP Error: {e.response.status_code}", "detail": e.response.text})
    except httpx.RequestError as e:
        return json.dumps({"error": f"Request Error: Could not connect to MCP server at {MCP_SERVER_URL}", "detail": str(e)})
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}"})

# --- Main Chat Logic ---

async def chat_loop():
    """
    The main loop for the chat application.
    """
    print("--- Obsidian MCP Chat Client ---")
    print(f"Model: {MODEL}")
    print(f"MCP Server: {MCP_SERVER_URL}")
    print("Type 'quit' or 'exit' to end the session.")
    print("-" * 35)

    # Initial messages for the LLM context
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": DEVELOPER_PROMPT + "\n\n" + TOOL_POLICY},
    ]
    
    # Prepare tool definitions for the OpenAI API
    tools = []
    for name, schema in TOOL_SCHEMAS.items():
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": schema.__doc__.strip(),
                "parameters": schema.model_json_schema()
            }
        })

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        
        # Add user message to history
        messages.append({"role": "user", "content": user_input})
        
        # --- Mandatory Execution Flow Step 1 & 2: Receive and Query ---
        
        # First API call: LLM decides whether to call a tool
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto", # Let the model decide
        )
        
        response_message = response.choices[0].message
        
        # --- Mandatory Execution Flow Step 3: Analyze the MCP result ---
        
        # Check if the LLM decided to call a tool
        if response_message.tool_calls:
            messages.append(response_message) # Add the tool call request to history
            
            # Execute all tool calls in parallel
            tool_outputs = []
            for tool_call in response_message.tool_calls:
                print(f"-> Calling MCP Tool: {tool_call.function.name} with args: {tool_call.function.arguments}")
                
                # Execute the tool call
                output = await call_mcp_tool(tool_call)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": output,
                })
                print(f"<- Tool Result (partial): {output[:100]}...")
            
            # Add tool results to history
            messages.extend(tool_outputs)
            
            # Second API call: LLM generates the final response based on tool results
            # --- Mandatory Execution Flow Step 4: Generate a response ---
            final_response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
            )
            
            final_response_message = final_response.choices[0].message
            print(f"\nAssistant: {final_response_message.content}")
            messages.append(final_response_message) # Add final response to history
            
        else:
            # This should not happen if the DEVELOPER_PROMPT is effective ("MUST query the Obsidian vault")
            # But we handle it as a fallback.
            print("\nAssistant: [ERROR] The model failed to call the mandatory MCP tool. Please rephrase your query.")
            messages.append(response_message) # Add the non-tool response to history

if __name__ == "__main__":
    import asyncio
    # Run the asynchronous chat loop
    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        print("\nSession ended by user.")
    except Exception as e:
        print(f"\nAn unrecoverable error occurred: {e}")

# Note on Python Best Practices:
# - Used `asyncio` and `httpx.AsyncClient` for non-blocking I/O when calling the server.
# - Used `pydantic` for clear tool definitions and type hinting.
# - Used `dotenv` for configuration management.
# - Clear separation of concerns (prompts, vault manager, server, client).

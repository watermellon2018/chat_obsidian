import os
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the vault manager logic
from vault_manager import (
    get_all_markdown_files,
    read_file_content,
    search_vault,
    get_file_metadata,
)

app = FastAPI(
    title="Mock Obsidian MCP Server",
    description="A FastAPI server exposing a Model Context Protocol (MCP) interface to a mock Obsidian vault.",
    version="1.0.0",
)

# --- Pydantic Models for API Responses ---

class FileMetadata(BaseModel):
    name: str
    path: str
    tags: List[str]

class SearchResult(BaseModel):
    path: str
    snippet: str

class FileContent(BaseModel):
    content: str

# --- API Endpoints (MCP Tools) ---

@app.get("/api/v1/files", response_model=List[str], summary="List Vault Files")
async def list_vault_files(
    path: Optional[str] = Query(None, description="Optional subdirectory path to list files from.")
):
    """
    Lists all markdown file paths in the vault, relative to the vault root.
    """
    # In this mock, we ignore the 'path' query for simplicity and return all files
    # A more complex implementation would filter based on the path.
    return get_all_markdown_files()

@app.get("/api/v1/search", response_model=List[SearchResult], summary="Search Vault")
async def search_vault_endpoint(
    query: str = Query(..., description="Text or tag to search for."),
    search_type: str = Query("content", description="Type of search: 'content' or 'tag'.")
):
    """
    Searches for content or tags across all notes.
    """
    if search_type not in ["content", "tag"]:
        raise HTTPException(status_code=400, detail="search_type must be 'content' or 'tag'")
    
    return search_vault(query, search_type)

@app.get("/api/v1/read", response_model=FileContent, summary="Read File Content")
async def read_file_content_endpoint(
    path: str = Query(..., description="Relative path to the file in the vault.")
):
    """
    Reads the full content of a specific file.
    """
    content = read_file_content(path)
    if content is None:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    return FileContent(content=content)

@app.get("/api/v1/metadata", response_model=FileMetadata, summary="Get File Metadata")
async def get_file_metadata_endpoint(
    path: str = Query(..., description="Relative path to the file in the vault.")
):
    """
    Retrieves file metadata, including tags.
    """
    metadata = get_file_metadata(path)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    return FileMetadata(**metadata)

# --- Server Startup Logic ---

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.getenv("MCP_SERVER_PORT", 8000))
    print(f"Starting MCP Server on port {PORT}...")
    # Note: In a real scenario, we would run this in a separate process/thread.
    # For this sandbox, we will run it with `uvicorn` in the next step.
    # The `if __name__ == "__main__"` block is for local testing/development.
    # We will use the `uvicorn` command line tool for the actual execution.

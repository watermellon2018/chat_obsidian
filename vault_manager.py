import os
import re
from typing import List, Dict, Optional

VAULT_PATH = os.path.join(os.path.dirname(__file__), "vault")

def get_all_markdown_files(base_path: str = VAULT_PATH) -> List[str]:
    """Recursively finds all markdown files in the vault and returns their paths relative to the vault root."""
    markdown_files = []
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".md"):
                full_path = os.path.join(root, file)
                # Get path relative to VAULT_PATH
                relative_path = os.path.relpath(full_path, VAULT_PATH)
                markdown_files.append(relative_path)
    return markdown_files

def read_file_content(relative_path: str) -> Optional[str]:
    """Reads the content of a file from the vault."""
    full_path = os.path.join(VAULT_PATH, relative_path)
    if not os.path.exists(full_path):
        return None
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None

def extract_metadata(content: str) -> Dict:
    """Extracts metadata (e.g., tags) from the file content (assuming YAML front matter)."""
    metadata = {"tags": []}
    # Simple regex to find YAML front matter
    match = re.search(r"^\s*---\s*\n(.*?)\n\s*---\s*\n", content, re.DOTALL)
    if match:
        front_matter = match.group(1)
        # Simple tag extraction
        tag_match = re.search(r"tags:\s*\[(.*?)\]", front_matter)
        if tag_match:
            tags_str = tag_match.group(1).strip()
            tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
            metadata["tags"] = tags
    return metadata

def search_vault(query: str, search_type: str = "content") -> List[Dict]:
    """Performs a simple search across all markdown files."""
    results = []
    files = get_all_markdown_files()
    
    # Normalize query for case-insensitive search
    normalized_query = query.lower()

    for file_path in files:
        content = read_file_content(file_path)
        if not content:
            continue

        metadata = extract_metadata(content)
        
        if search_type == "content" and normalized_query in content.lower():
            # For simplicity, return the first 200 chars as a snippet
            snippet = content.replace("\n", " ")[:200] + "..."
            results.append({"path": file_path, "snippet": snippet})
        
        elif search_type == "tag":
            # Check if any tag matches the query
            if any(normalized_query.lstrip('#') == tag.lstrip('#').lower() for tag in metadata["tags"]):
                snippet = content.replace("\n", " ")[:200] + "..."
                results.append({"path": file_path, "snippet": snippet})

    return results

def get_file_metadata(relative_path: str) -> Optional[Dict]:
    """Retrieves file metadata."""
    content = read_file_content(relative_path)
    if not content:
        return None
    
    metadata = extract_metadata(content)
    metadata["name"] = os.path.basename(relative_path)
    metadata["path"] = relative_path
    return metadata

if __name__ == '__main__':
    # Simple test to ensure functions work
    print("--- All Files ---")
    files = get_all_markdown_files()
    print(files)
    
    if files:
        print("\n--- Metadata for first file ---")
        meta = get_file_metadata(files[0])
        print(meta)
        
        print("\n--- Search for 'MCP' ---")
        search_results = search_vault("MCP", "content")
        print(search_results)
        
        print("\n--- Search for tag 'Python' ---")
        tag_results = search_vault("Python", "tag")
        print(tag_results)

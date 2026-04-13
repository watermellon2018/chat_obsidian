import os
import sys
from pathlib import Path
from uuid import uuid4

# Repo root must be on path when running this file directly (not `python -m ...`).
_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from backend.db_script.embeddings import build_chunks


def main():
    model_embeddings = OpenAIEmbeddings(
        model="openai/text-embedding-3-small",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
    )
    
    vault_path = os.getenv("VAULT_PATH")
    if not vault_path:
        print("Error: Specify VAULT_PATH in .env file")
        return
    chunks = build_chunks(Path(vault_path))
    uuids = [str(uuid4()) for _ in range(len(chunks))]

    print(f"Create database from {len(chunks)} fragments. This may take time...")
    vector_store = FAISS.from_documents(chunks, model_embeddings, ids=uuids)

    index_path = os.getenv("SAVE_INDEX_PATH")
    if not index_path:
        print("Error: Specify SAVE_INDEX_PATH in .env file")
        return
    
    Path(index_path).mkdir(parents=True, exist_ok=True)
    vector_store.save_local(index_path)
    print(f"Database saved to {index_path}")

if __name__ == "__main__":
    main()

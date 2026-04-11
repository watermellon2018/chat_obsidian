import getpass
import os
import sys
from pathlib import Path
from uuid import uuid4

# Repo root must be on path when running this file directly (not `python -m ...`).
_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

from backend.db_script.embeddings import build_chunks

if not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = getpass.getpass("Enter your Google API key: ")


def main():
    model_embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2-preview",
                                                    api_key=os.getenv("GEMINI_API_KEY"),
                                                    task_type='RETRIEVAL_DOCUMENT')
    
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

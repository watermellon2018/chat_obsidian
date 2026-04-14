import os
import sys
from pathlib import Path
from uuid import uuid4

# Repo root must be on path when running this file directly (not `python -m ...`).
_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from langchain_community.vectorstores import FAISS

from backend.db_script.embeddings import build_chunks


def main():
    # Для использования Qwen3-Embedding-8B через OpenRouter, 
    # langchain_openai.OpenAIEmbeddings не поддерживает кастомные модели 
    # (как Qwen) через OpenRouter, потому что они нельзя вызвать embedding через обычный openai endpoint.
    # Можно сделать руками: HTTP запрос к openrouter.ai/api/v1/embeddings, соблюдая их формат.
    import httpx

    class OpenRouterQwenEmbeddings:
        def __init__(self, api_key: str, model: str, api_base: str = "https://openrouter.ai/api/v1"):
            self.api_key = api_key
            self.model = model
            self.api_base = api_base

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            # OpenRouter ожидает один документ на запрос
            res = []
            for text in texts:
                resp = httpx.post(
                    f"{self.api_base}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "http://localhost",
                        "X-Title": "obsidian-chat"
                    },
                    json={
                        "model": self.model,
                        "input": text,
                    }
                )
                resp.raise_for_status()
                res.append(resp.json()["data"][0]["embedding"])
            return res

        def embed_query(self, text: str) -> list[float]:
            resp = httpx.post(
                f"{self.api_base}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "obsidian-chat"
                },
                json={
                    "model": self.model,
                    "input": text,
                }
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]

    model_embeddings = OpenRouterQwenEmbeddings(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="qwen/qwen3-embedding-8b"
    )
    
    vault_path = os.getenv("VAULT_PATH")
    if not vault_path:
        print("Error: Specify VAULT_PATH in .env file")
        return
    chunks = build_chunks(Path(vault_path))
    uuids = [str(uuid4()) for _ in range(len(chunks))]

    print(f"Create database from {len(chunks)} fragments. This may take time...")
    vector_store = FAISS.from_documents(chunks, model_embeddings, ids=uuids, chunk_size=20)

    index_path = os.getenv("SAVE_INDEX_PATH")
    if not index_path:
        print("Error: Specify SAVE_INDEX_PATH in .env file")
        return
    
    Path(index_path).mkdir(parents=True, exist_ok=True)
    vector_store.save_local(index_path)
    print(f"Database saved to {index_path}")

if __name__ == "__main__":
    main()

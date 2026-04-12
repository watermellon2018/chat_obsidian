"""
Entry point for the Obsidian MCP Chat system.

Usage:
    python run.py                          # Web UI on :7860 (default)
    python run.py --port 8080              # Custom port
    python run.py --model ollama           # Local Ollama
    python run.py --ui cli                 # Terminal chat
    python run.py --model ollama --ollama-model llama3.2:3b

Prerequisites:
    Gemini:  Set GEMINI_API_KEY in .env  (https://aistudio.google.com)
    Ollama:  `ollama serve` running + model pulled
             e.g. `ollama pull qwen2.5:7b-instruct-q4_K_M`
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# ── Add backend/ to sys.path so all backend imports resolve correctly ────────
BACKEND_DIR = Path(__file__).parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from config import Config  # noqa: E402  (import after sys.path setup)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Obsidian MCP Chat — knowledge-first assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        choices=["gemini", "ollama"],
        default="gemini",
        help="Model backend (default: gemini)",
    )
    parser.add_argument(
        "--ollama-model",
        default=None,
        metavar="MODEL_NAME",
        help="Ollama model name (overrides OLLAMA_MODEL env var)",
    )
    parser.add_argument(
        "--ui",
        choices=["web", "cli"],
        default="web",
        help="Interface: 'web' (FastAPI, default) or 'cli' (terminal)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port for the web UI (default: 7860)",
    )
    return parser.parse_args()


def build_model(config: Config):
    if config.model_backend == "gemini":
        from model.gemini_model import GeminiModel

        if not config.gemini_api_key:
            print(
                "ERROR: GEMINI_API_KEY is not set.\n"
                "  1. Go to https://aistudio.google.com\n"
                "  2. Click 'Get API key' → Create API key\n"
                "  3. Add to .env:  GEMINI_API_KEY=your_key",
                file=sys.stderr,
            )
            sys.exit(1)
        return GeminiModel(config)

    if config.model_backend == "ollama":
        from model.ollama_model import OllamaModel
        return OllamaModel(config)

    raise ValueError(f"Unknown model backend: {config.model_backend!r}")


def run_web(model, config: Config, port: int) -> None:
    import uvicorn
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from api.app import create_app

    app = create_app(model, config)

    frontend_src = Path(__file__).parent / "frontend" / "src"
    frontend_html = frontend_src / "index.html"

    # Serve JS modules at /js — required for ES module imports in index.html.
    # In production nginx serves the whole frontend/src/ directory directly.
    app.mount("/js", StaticFiles(directory=str(frontend_src / "js")), name="js")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(frontend_html))

    print(f"Starting Obsidian MCP Chat → http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


async def run_cli(model, config: Config) -> None:
    from client.mcp_client import MCPClient
    from services.orchestrator import Orchestrator

    print("\033[1mObsidian MCP Chat (CLI)\033[0m")
    print("Your notes are the primary source of truth.")
    print("Type \033[1mquit\033[0m or press Ctrl+C to exit.")
    print("-" * 50)

    async with MCPClient() as mcp_client:
        orchestrator = Orchestrator(model, mcp_client, config)
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break
            if not user_input or user_input.lower() in ("quit", "exit", "выход"):
                print("Goodbye!")
                break
            answer = await orchestrator.handle_query(user_input)
            print(f"\nBot: {answer}")


def main() -> None:
    args = parse_args()

    config = Config(model_backend=args.model)
    if args.ollama_model:
        config.ollama_model = args.ollama_model

    model = build_model(config)

    if args.ui == "web":
        run_web(model, config, args.port)
    else:
        asyncio.run(run_cli(model, config))


if __name__ == "__main__":
    main()

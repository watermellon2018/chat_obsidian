"""
Entry point for the Obsidian MCP Chat system.

Usage:
    python run.py                                      # Web UI on :7860 (default)
    python run.py --ui web --port 8080                 # Custom port
    python run.py --ui cli                             # Terminal chat
    python run.py --model ollama                       # Local Ollama
    python run.py --model ollama --ollama-model llama3.2:3b

Prerequisites:
    Gemini:  Set GEMINI_API_KEY in .env  (get key: https://aistudio.google.com)
    Ollama:  `ollama serve` running + model pulled
             e.g. `ollama pull qwen2.5:7b-instruct-q4_K_M`
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from config import Config


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

    elif config.model_backend == "ollama":
        from model.ollama_model import OllamaModel
        return OllamaModel(config)

    raise ValueError(f"Unknown model backend: {config.model_backend!r}")


def run_web(model, config: Config, port: int) -> None:
    import uvicorn
    import ui.web as web_module

    # Inject model + config before uvicorn starts accepting requests
    web_module._model = model
    web_module._config = config

    print(f"Starting Obsidian MCP Chat → http://localhost:{port}")
    uvicorn.run(web_module.app, host="0.0.0.0", port=port, log_level="warning")


async def run_cli(model, config: Config) -> None:
    from client.mcp_client import MCPClient
    from client.orchestrator import Orchestrator
    from ui.cli import CLI

    async with MCPClient() as mcp_client:
        orchestrator = Orchestrator(model, mcp_client, config)
        cli = CLI(orchestrator)
        await cli.run()


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

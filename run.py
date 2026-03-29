"""
Entry point for the Obsidian MCP Chat system.

Usage:
    python run.py --model gemini                           # Google Gemini 2.0 Flash
    python run.py --model ollama                           # Local Ollama (default model from .env)
    python run.py --model ollama --ollama-model llama3.2:3b  # specific Ollama model

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
    return parser.parse_args()


def build_model(config: Config):
    if config.model_backend == "gemini":
        from model.gemini_model import GeminiModel

        if not config.gemini_api_key:
            print(
                "ERROR: GEMINI_API_KEY is not set.\n"
                "  1. Go to https://aistudio.google.com\n"
                "  2. Click 'Get API key' → Create API key\n"
                "  3. Copy the key into your .env file as GEMINI_API_KEY=...",
                file=sys.stderr,
            )
            sys.exit(1)
        return GeminiModel(config)

    elif config.model_backend == "ollama":
        from model.ollama_model import OllamaModel

        return OllamaModel(config)

    raise ValueError(f"Unknown model backend: {config.model_backend!r}")


async def main() -> None:
    args = parse_args()

    config = Config(model_backend=args.model)
    if args.ollama_model:
        config.ollama_model = args.ollama_model

    model = build_model(config)

    from client.mcp_client import MCPClient
    from client.orchestrator import Orchestrator
    from ui.cli import CLI

    async with MCPClient() as mcp_client:
        orchestrator = Orchestrator(model, mcp_client, config)
        cli = CLI(orchestrator)
        await cli.run()


if __name__ == "__main__":
    asyncio.run(main())

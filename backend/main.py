"""
Backend entry point.

Usage (development):
    python main.py                        # OpenRouter, port 8000
    python main.py --model ollama         # Local Ollama
    python main.py --model gemini         # Google Gemini
    python main.py --port 9000            # Custom port

Usage (production via Docker):
    Set MODEL_BACKEND, OPENROUTER_API_KEY / GEMINI_API_KEY / OLLAMA_MODEL env vars,
    then: uvicorn main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import argparse
import os
import sys

from config import Config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Obsidian MCP Backend")
    parser.add_argument(
        "--model",
        choices=["openrouter", "gemini", "ollama"],
        default=os.getenv("MODEL_BACKEND", "openrouter"),
    )
    parser.add_argument(
        "--ollama-model",
        default=None,
        metavar="MODEL_NAME",
        help="Override OLLAMA_MODEL env var",
    )
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    return parser.parse_args()


def build_model(config: Config):
    if config.model_backend == "openrouter":
        from model.openrouter_model import OpenRouterModel

        if not config.openrouter_api_key:
            print(
                "ERROR: OPENROUTER_API_KEY is not set.\n"
                "  Set it in .env or as an environment variable.",
                file=sys.stderr,
            )
            sys.exit(1)
        return OpenRouterModel(config)

    if config.model_backend == "gemini":
        from model.gemini_model import GeminiModel

        if not config.gemini_api_key:
            print(
                "ERROR: GEMINI_API_KEY is not set.\n"
                "  Set it in .env or as an environment variable.",
                file=sys.stderr,
            )
            sys.exit(1)
        return GeminiModel(config)

    if config.model_backend == "ollama":
        from model.ollama_model import OllamaModel
        return OllamaModel(config)

    raise ValueError(f"Unknown model backend: {config.model_backend!r}")


def _build_app():
    """Called at module level so `uvicorn main:app` works without CLI args."""
    from api.app import create_app

    config = Config(model_backend=os.getenv("MODEL_BACKEND", "openrouter"))
    model = build_model(config)
    return create_app(model, config)


# Module-level `app` so uvicorn can import it directly.
app = _build_app()


if __name__ == "__main__":
    import uvicorn

    args = parse_args()
    config = Config(model_backend=args.model)
    if args.ollama_model:
        config.ollama_model = args.ollama_model

    model = build_model(config)

    from api.app import create_app
    application = create_app(model, config)

    print(f"Backend → http://{args.host}:{args.port}")
    uvicorn.run(application, host=args.host, port=args.port, log_level="info")

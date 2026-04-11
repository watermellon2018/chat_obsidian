from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    vault_path: Path = field(
        default_factory=lambda: Path(os.getenv("VAULT_PATH", "./vault")).resolve()
    )
    model_backend: str = "gemini"  # "gemini" | "ollama"

    # Gemini
    gemini_api_key: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )
    gemini_model: str = "gemini-2.5-flash"

    # Ollama
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
    )
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )

    # Orchestrator safeguard
    max_tool_rounds: int = 10

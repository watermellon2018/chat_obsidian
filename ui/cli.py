"""Interactive command-line interface."""
from __future__ import annotations

import asyncio
import sys

from client.orchestrator import Orchestrator


class CLI:
    def __init__(self, orchestrator: Orchestrator) -> None:
        self._orch = orchestrator

    async def run(self) -> None:
        print("\033[1mObsidian MCP Chat\033[0m")
        print("Your notes are the primary source of truth.")
        print("Type \033[1mquit\033[0m or press Ctrl+C to exit.")
        print("-" * 50)

        try:
            while True:
                try:
                    user_input = input("\n\033[1mYou:\033[0m ").strip()
                except EOFError:
                    break

                if not user_input:
                    continue

                if user_input.lower() in ("quit", "exit", "q"):
                    break

                try:
                    answer = await self._orch.handle_query(user_input)
                    print(f"\n\033[1mAssistant:\033[0m {answer}")
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    print(f"\n\033[31m[ERROR] {exc}\033[0m", file=sys.stderr)

        except KeyboardInterrupt:
            pass

        print("\nSession ended.")

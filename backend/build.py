"""GraphBus Build Mode entry point.

When ``graphbus`` is installed, this script invokes the LLM-powered
build pipeline that lets agents negotiate changes to each other's
schemas and behaviour. Without the package it prints setup instructions.
"""

from __future__ import annotations

import sys


def main() -> None:
    """Run graphbus build mode or print instructions."""
    try:
        from graphbus_core.build.builder import build_project  # type: ignore[import-untyped]

        print("Starting GraphBus Build Mode …")
        build_project()
    except ImportError:
        print(
            "graphbus package is not installed.\n"
            "\n"
            "To enable Build Mode (LLM-powered agent negotiation):\n"
            "  pip install graphbus\n"
            "\n"
            "Then set at least one LLM key in .env:\n"
            "  DEEPSEEK_API_KEY=…\n"
            "  ANTHROPIC_API_KEY=…\n"
            "\n"
            "Re-run: python build.py\n"
            "\n"
            "More info: https://graphbus.com/docs/build-mode"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

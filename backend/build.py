"""GraphBus Build Mode entry point.

Runs the LLM-powered build pipeline: agents analyse their own code,
propose improvements, evaluate each other's proposals, and commit
consensus changes to disk.

Requirements
------------
1. A GraphBus API key (get one at https://graphbus.com/onboarding)
2. At least one LLM provider key (DeepSeek, Anthropic, or OpenRouter)

Usage
-----
    cp .env.example .env   # fill in GRAPHBUS_API_KEY + an LLM key
    python build.py
    python build.py --dry-run   # analyse only, no file writes
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Gate 1 — GraphBus API key
# ---------------------------------------------------------------------------

GRAPHBUS_API_KEY = os.getenv("GRAPHBUS_API_KEY", "").strip()
if not GRAPHBUS_API_KEY:
    print(
        "\n"
        "╔══════════════════════════════════════════════════════════════╗\n"
        "║          GRAPHBUS_API_KEY is required for Build Mode         ║\n"
        "╠══════════════════════════════════════════════════════════════╣\n"
        "║  1. Sign up (free) at https://graphbus.com/onboarding        ║\n"
        "║  2. Copy your API key                                        ║\n"
        "║  3. Add it to your .env file:                                ║\n"
        "║        GRAPHBUS_API_KEY=gb_...                               ║\n"
        "╚══════════════════════════════════════════════════════════════╝\n",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"✓  GraphBus API key found ({GRAPHBUS_API_KEY[:8]}…)")


# ---------------------------------------------------------------------------
# Gate 2 — LLM provider key
# ---------------------------------------------------------------------------

LLM_KEYS = {
    "DEEPSEEK_API_KEY": "deepseek-reasoner (recommended)",
    "ANTHROPIC_API_KEY": "claude-sonnet",
    "OPENROUTER_API_KEY": "any model via OpenRouter",
    "OPENAI_API_KEY": "gpt-4o",
}

active_llm_key = next((k for k in LLM_KEYS if os.getenv(k, "").strip()), None)

if not active_llm_key:
    print(
        "\n"
        "⚠️  No LLM API key found — Build Mode requires one.\n"
        "   Add one of these to your .env file:\n"
        + "".join(f"     {k}=...   # {desc}\n" for k, desc in LLM_KEYS.items())
        + "\n   Docs: https://graphbus.com/docs/build-mode\n",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"✓  LLM provider: {LLM_KEYS[active_llm_key]}")


# ---------------------------------------------------------------------------
# Run build
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="GraphBus build — LLM negotiation cycle")
    parser.add_argument("--dry-run", action="store_true", help="Analyse only — no file writes")
    args = parser.parse_args()

    try:
        from graphbus_core.config import BuildConfig
        from graphbus_core.build.builder import build_project
    except ImportError as exc:
        print(f"✗  graphbus not installed: {exc}\n   Run: pip install graphbus", file=sys.stderr)
        sys.exit(1)

    config = BuildConfig(
        root_package="agents",
        output_dir=".graphbus",
    )

    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Starting negotiation cycle…")
    print("Agents: UserRegistrationAgent, AuthAgent, TaskManagerAgent, NotificationAgent\n")

    try:
        artifacts = build_project(config, enable_agents=not args.dry_run)
        print("\n✓  Build complete")
        print(f"   Artifacts: {artifacts.output_dir}")
        if hasattr(artifacts, "modified_files") and artifacts.modified_files:
            print(f"   Modified:  {len(artifacts.modified_files)} file(s)")
            for f in artifacts.modified_files:
                print(f"     - {f}")
        else:
            print("   No files modified (agents reached consensus without changes)")
    except Exception as exc:
        print(f"\n✗  Build failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

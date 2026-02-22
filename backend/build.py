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

from graphbus_core.auth import ensure_api_key, check_llm_key, get_configured_model

# ---------------------------------------------------------------------------
# Gate 1 — GraphBus API key (interactive onboarding if not configured)
# ---------------------------------------------------------------------------

GRAPHBUS_API_KEY = ensure_api_key()
print(f"✓  GraphBus API key ({GRAPHBUS_API_KEY[:8]}…)")


# ---------------------------------------------------------------------------
# Gate 2 — LLM provider key (checked in env, never stored)
# ---------------------------------------------------------------------------

llm_found, llm_env_var, llm_model = check_llm_key()

if not llm_found:
    print(
        f"\n⚠️  {llm_env_var} not found in environment.\n"
        f"   Your configured model requires it:\n"
        f"     export {llm_env_var}=your_key_here\n"
        f"\n   To change your model preference, run: graphbus auth login\n"
        f"   Docs: https://graphbus.com/docs/build-mode\n",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"✓  LLM model: {llm_model}  (via {llm_env_var})")


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

    from graphbus_core.config import LLMConfig
    config = BuildConfig(
        root_package="agents",
        output_dir=".graphbus",
        llm_config=LLMConfig(model=llm_model),
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

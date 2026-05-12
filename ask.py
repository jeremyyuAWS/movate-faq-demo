#!/usr/bin/env python3
"""ask.py — Movate FAQ orchestrator.

Routes a CLI question through the manager → expert pattern:

    1. Manager classifies the question into one of three lanes:
       scaffold / eval-bench / deploy-ops
    2. Right expert agent answers with KB-grounded confidence

Runs the agents either **locally** (default — needs OPENAI + ANTHROPIC
keys) or **against a deployed runtime** (--remote, hits Azure).

This file replaces what a v1.1 ``workflow.yaml`` with conditional
``when:`` edges will eventually express declaratively. Same behavior,
just expressed in 40 lines of Python until that ships.

Usage:
    python ask.py "How do I scaffold a classifier agent?"
    python ask.py "How do I gate on eval pass rate?" --remote dev
    python ask.py "How do I deploy to Azure?" --mock
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

VALID_LANES = {"scaffold", "eval-bench", "deploy-ops"}


def run_agent_local(agent: str, payload: dict, *, mock: bool = False) -> dict:
    """Run an agent locally via `movate run`. Returns the parsed response."""
    cmd = ["movate", "run", f"agents/{agent}", json.dumps(payload), "-o", "json"]
    if mock:
        cmd.append("--mock")
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def submit_agent_remote(agent: str, payload: dict, *, target: str) -> dict:
    """Submit + wait on a deployed runtime via `movate submit ... --wait`."""
    cmd = [
        "movate", "submit", agent, json.dumps(payload),
        "--target", target, "--wait", "-o", "json",
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def ask(question: str, *, remote: str | None = None, mock: bool = False) -> None:
    payload = {"question": question}
    runner = (
        (lambda a, p: submit_agent_remote(a, p, target=remote))
        if remote
        else (lambda a, p: run_agent_local(a, p, mock=mock))
    )

    print(f"→ asking manager to classify: {question!r}", file=sys.stderr)
    decision = runner("manager", payload)
    lane = decision.get("data", {}).get("classification")

    if lane not in VALID_LANES:
        print(f"✗ manager returned unknown lane: {lane!r}", file=sys.stderr)
        print(f"  full response: {json.dumps(decision, indent=2)}", file=sys.stderr)
        sys.exit(2)

    print(f"→ routed to: expert-{lane}", file=sys.stderr)
    answer = runner(f"expert-{lane}", payload)

    # Pretty print final answer
    data = answer.get("data", {})
    print(f"\n📚 Answer (confidence: {data.get('confidence', 'N/A')}):")
    print(data.get("answer", "<no answer>"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ask the Movate FAQ — manager + expert routing pattern."
    )
    parser.add_argument("question", nargs="+", help="The question to ask")
    parser.add_argument(
        "--remote",
        metavar="TARGET",
        help="Run against a deployed runtime (e.g. --remote dev)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use MockProvider (no API spend; for smoke tests)",
    )
    args = parser.parse_args()

    if args.remote and args.mock:
        parser.error("--remote and --mock are mutually exclusive")

    question = " ".join(args.question)
    ask(question, remote=args.remote, mock=args.mock)


if __name__ == "__main__":
    main()

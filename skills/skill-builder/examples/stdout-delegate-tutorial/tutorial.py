#!/usr/bin/env python3
"""
3-step chained stdout-delegate demo.

Each --step emits one __LLM_DELEGATE__ directive with an `out` file.
The provider writes the LLM response into that file, then runs the next step.
No API key, no CLI, no SDK — just stdout and tmp files.
"""

import argparse
import json
from pathlib import Path

TMP = Path("tmp/tutorial")


def delegate(prompt: str, out: Path) -> None:
    # Intentional inline implementation — this tutorial demonstrates the raw
    # wire protocol in ~2 lines. Real scripts should copy scripts/delegate.py
    # (or import agent.call_emit) rather than re-implementing this.
    directive = {"prompt": prompt, "out": str(out)}
    print(f"__LLM_DELEGATE__: {json.dumps(directive)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="3-step stdout-delegate chain demo")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4], default=1,
                        help="Which step to run (1-3 emit directives; 4 prints the result)")
    args = parser.parse_args()

    TMP.mkdir(parents=True, exist_ok=True)

    if args.step == 1:
        delegate(
            "Name one obscure programming language. Reply with the name only.",
            TMP / "lang.txt",
        )

    elif args.step == 2:
        lang = (TMP / "lang.txt").read_text().strip()
        delegate(
            f"Give one surprising fact about {lang} in one sentence.",
            TMP / "fact.txt",
        )

    elif args.step == 3:
        lang = (TMP / "lang.txt").read_text().strip()
        fact = (TMP / "fact.txt").read_text().strip()
        delegate(
            f"Given this fact about {lang}: '{fact}' — should a beginner learn it? One sentence.",
            TMP / "verdict.txt",
        )

    elif args.step == 4:
        lang    = (TMP / "lang.txt").read_text().strip()
        fact    = (TMP / "fact.txt").read_text().strip()
        verdict = (TMP / "verdict.txt").read_text().strip()
        print("=== Chain complete ===")
        print(f"Language : {lang}")
        print(f"Fact     : {fact}")
        print(f"Verdict  : {verdict}")


if __name__ == "__main__":
    main()

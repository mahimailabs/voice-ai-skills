#!/usr/bin/env python3
"""Check measured voice agent timings against the budget for a pipeline shape.

Example:
    python scripts/latency_budget.py --shape cascade \
        --eot 700 --stt 150 --ttft 620 --ttfb 240 --e2e 1560

Stages marked n/a are folded into the model for that shape and are not scored.
See skills/voice-latency-budget/SKILL.md for where the numbers come from.
"""

from __future__ import annotations

import argparse
import sys

STAGES = ["eot", "stt", "ttft", "ttfb", "e2e"]

LABELS = {
    "eot": "end-of-turn delay",
    "stt": "transcription delay",
    "ttft": "LLM time to first token",
    "ttfb": "TTS time to first byte",
    "e2e": "end to end",
}

# Budget ceiling in milliseconds per stage, per shape. None means not scored.
BUDGETS = {
    "cascade": {"eot": 500, "stt": 200, "ttft": 400, "ttfb": 300, "e2e": 800},
    "s2s": {"eot": 300, "stt": None, "ttft": None, "ttfb": None, "e2e": 500},
    "full-duplex": {"eot": None, "stt": None, "ttft": 700, "ttfb": None, "e2e": 300},
}

# Order of fixes. First stage in this list that is over budget is the one to fix.
FIX_ORDER = ["eot", "ttft", "ttfb", "stt", "e2e"]

FIXES = {
    "eot": "Cut the endpointing min delay first. 0.5 s without a turn model, 0.3 s with one.",
    "ttft": "Turn on preemptive generation, then cut prompt size, then drop to a smaller model.",
    "ttfb": "Stream TTS from the first sentence. If it already streams, move TTS into the agent region.",
    "stt": "Move to streaming transcription and put the STT provider in the agent region.",
    "e2e": "Stages are inside budget but the total is not. The loss is network. Co-locate every hop.",
}


def row(stage: str, measured: float | None, budget: int | None) -> tuple[str, float | None]:
    label = LABELS[stage].ljust(24)
    if budget is None:
        shown = "-" if measured is None else f"{measured:.0f} ms"
        return f"  {label} {shown.rjust(9)}   n/a for this shape", None
    target = f"<= {budget} ms"
    if measured is None:
        return f"  {label} {'not measured'.rjust(9)}   {target}   MEASURE IT", None
    over = measured - budget
    verdict = "ok" if over <= 0 else f"OVER by {over:.0f} ms"
    return f"  {label} {f'{measured:.0f} ms'.rjust(9)}   {target}   {verdict}", (over if over > 0 else None)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check measured voice agent timings against the budget for a pipeline shape.",
        epilog="Example: python scripts/latency_budget.py --shape cascade --eot 700 --ttft 620 --ttfb 240 --e2e 1560",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--shape", choices=sorted(BUDGETS), default="cascade", help="pipeline shape being measured")
    for stage in STAGES:
        parser.add_argument(f"--{stage}", type=float, default=None, help=f"{LABELS[stage]} in milliseconds")
    args = parser.parse_args()

    measured = {stage: getattr(args, stage) for stage in STAGES}
    if all(value is None for value in measured.values()):
        parser.error("give at least one measurement, for example --e2e 1560")

    budgets = BUDGETS[args.shape]
    print(f"\nshape: {args.shape}   (all values in milliseconds, p50 unless you say otherwise)\n")

    overruns: dict[str, float] = {}
    for stage in STAGES:
        line, over = row(stage, measured[stage], budgets[stage])
        print(line)
        if over is not None:
            overruns[stage] = over

    print()
    if not overruns:
        print("  Every measured stage is inside budget. Measure p95 next, then measure on a phone call.")
        return 0

    stages_over = {k: v for k, v in overruns.items() if k != "e2e"} or overruns
    worst = max(stages_over, key=lambda stage: stages_over[stage])
    print(f"  worst stage:  {LABELS[worst]}, over by {overruns[worst]:.0f} ms")
    first = next(stage for stage in FIX_ORDER if stage in overruns)
    print(f"  fix first:    {LABELS[first]}")
    print(f"                {FIXES[first]}")
    if first != worst:
        print(f"  note:         {LABELS[worst]} is further over, but fixing {LABELS[first]} is cheaper and often moves it.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

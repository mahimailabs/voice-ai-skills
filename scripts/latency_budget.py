#!/usr/bin/env python3
"""Repository entry point for the helper bundled with voice-latency-budget."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "skills" /
                      "voice-latency-budget" / "scripts" / "latency_budget.py"),
                   run_name="__main__")

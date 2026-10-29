"""Load the per-skill behavioral scenarios and grade an answer against them.

Each skill has tests/scenarios/<skill>.json. A scenario holds a prompt, required and
forbidden regular expressions (case-insensitive), prose criteria for a human
reviewer, and a passing and a failing example answer that keep the patterns honest.
Patterns are a floor, not a verdict: a pass still needs the criteria reviewed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / 'tests' / 'scenarios'
FLAGS = re.IGNORECASE | re.MULTILINE


def load(directory: Path = SCENARIOS) -> dict[str, dict]:
    """Return {skill: file contents} for every scenario file."""
    return {path.stem: json.loads(path.read_text(encoding='utf-8'))
            for path in sorted(directory.glob('*.json'))}


def cases(directory: Path = SCENARIOS) -> list[dict]:
    """Flatten every scenario, tagged with the skill it expects to load."""
    return [{**scenario, 'expected_skill': skill}
            for skill, data in load(directory).items() for scenario in data['scenarios']]


def grade(scenario: dict, answer: str) -> dict:
    """Check an answer. Returns the missing required and the matched forbidden patterns."""
    missing = [rule for rule in scenario['required'] if not re.search(rule['pattern'], answer, FLAGS)]
    hit = [rule for rule in scenario['forbidden'] if re.search(rule['pattern'], answer, FLAGS)]
    return {'passed': not missing and not hit,
            'missing': [rule['why'] for rule in missing],
            'forbidden': [rule['why'] for rule in hit]}

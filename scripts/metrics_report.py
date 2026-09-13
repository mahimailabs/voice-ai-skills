#!/usr/bin/env python3
"""Report p50/p95 in seconds from clinic voice_metrics log snapshots.

Usage: python scripts/metrics_report.py call.log
Merges repeated snapshots by scope/role/turn ID. Missing samples are not zero.
LiveKit user and assistant messages remain separate populations.
"""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

NAMES = ('transcription_delay', 'end_of_turn_delay', 'llm_node_ttft', 'tts_node_ttfb', 'e2e_latency')


def summarize(lines):
    turns = {}
    for line in lines:
        if 'voice_metrics ' not in line:
            continue
        record = json.loads(line.split('voice_metrics ', 1)[1])
        key = (record['scope'], record['role'], record['turn_id'])
        current = turns.setdefault(key, {})
        for name in NAMES:
            value = record.get(name)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
                current[name] = value
    groups = defaultdict(list)
    for (scope, role, _), values in turns.items():
        groups[(scope, role)].append(values)
    result = []
    for (scope, role), rows in sorted(groups.items()):
        metrics = {}
        for name in NAMES:
            samples = sorted(row[name] for row in rows if name in row)
            n = len(samples)
            metrics[name] = {'samples': n, 'missing': len(rows)-n,
                             'p50': samples[math.ceil(n*.5)-1] if n else None,
                             'p95': samples[math.ceil(n*.95)-1] if n else None}
        result.append({'scope': scope, 'role': role, 'turns': len(rows), 'metrics': metrics})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.log.read_text().splitlines()), indent=2))

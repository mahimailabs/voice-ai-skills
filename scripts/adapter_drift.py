#!/usr/bin/env python3
"""Report adapters whose pinned stack version or verification date has drifted.

Reads the stamp under every "### <stack>" heading in each skill's "## Adapters"
section, plus the SDK pins in the CI workflow, and compares them with the releases
published on PyPI. An adapter is due for a refresh when its stack has shipped a newer
minor or major release, or when it was verified more than 90 days ago; stale after 180
(docs/neutrality.md). Drift is reported, never a CI failure.

Usage:
    python scripts/adapter_drift.py [--summary FILE] [--open-issues]
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'validate.yml'
DUE_DAYS, STALE_DAYS = 90, 180
STABLE = re.compile(r'^\d+(\.\d+)*$')

spec = importlib.util.spec_from_file_location('validator', ROOT / 'scripts' / 'validate.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split('.'))


def pypi_releases(package: str) -> list[str]:
    with urllib.request.urlopen(f'https://pypi.org/pypi/{package}/json', timeout=30) as reply:
        data = json.load(reply)
    return sorted((v for v, files in data['releases'].items() if STABLE.match(v) and files), key=version)


def behind(pinned: str, releases: list[str]) -> tuple[int, int]:
    """Releases newer than the pin, and how many of those open a new minor or major.

    A two-part pin such as 1.8 names a series, so patches inside it do not count.
    """
    pin = version(pinned)
    width = len(pin)
    newer = [v for v in releases if version(v)[:width] > pin] if width < 3 else \
        [v for v in releases if version(v) > pin]
    series = {version(v)[:2] for v in newer if version(v)[:2] > pin[:2]}
    return len(newer), len(series)


def collect() -> tuple[list[dict], list[dict]]:
    adapters = []
    for skill in sorted((ROOT / 'skills').iterdir()):
        path = skill / 'SKILL.md'
        if path.is_file():
            failures: list = []
            for stamp in validator.adapter_stamps(path.read_text(encoding='utf-8'), str(path), failures):
                adapters.append({'skill': skill.name, **stamp})
    pins = [{'package': p, 'pinned': v} for p, v in
            re.findall(r"'([a-z0-9-]+)(?:\[[^\]]*\])?==([0-9.]+)'", WORKFLOW.read_text(encoding='utf-8'))]
    return adapters, pins


def assess(adapters: list[dict], pins: list[dict], releases: dict[str, list[str]], today: dt.date) -> None:
    for row in adapters:
        row['age'] = (today - dt.date.fromisoformat(row['verified'])).days
        known = row['pinned'] != 'unversioned' and row['package'] in releases
        row['latest'] = releases[row['package']][-1] if known else 'n/a'
        row['behind'], new_series = behind(row['pinned'], releases[row['package']]) if known else (0, 0)
        reasons = []
        if new_series:
            reasons.append(f'{new_series} newer minor or major release(s)')
        if row['age'] > DUE_DAYS:
            reasons.append(f'verified {row["age"]} days ago')
        row['status'] = 'stale' if row['age'] > STALE_DAYS else 'due' if reasons else 'ok'
        row['reasons'] = reasons
    for row in pins:
        row['latest'] = releases[row['package']][-1] if row['package'] in releases else 'n/a'
        row['behind'] = behind(row['pinned'], releases[row['package']])[0] if row['package'] in releases else 0


def report(adapters: list[dict], pins: list[dict], today: dt.date) -> str:
    lines = [f'# Adapter drift, {today.isoformat()}', '',
             '| skill | stack | pinned | latest | releases behind | verified | age (days) | status |',
             '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in adapters:
        lines.append(f"| {r['skill']} | {r['stack']} | {r['pinned']} | {r['latest']} | {r['behind']} | "
                     f"{r['verified']} | {r['age']} | {r['status']} |")
    lines += ['', '## SDK contract pins in CI', '', '| package | pinned | latest | releases behind |',
              '| --- | --- | --- | --- |']
    lines += [f"| {p['package']} | {p['pinned']} | {p['latest']} | {p['behind']} |" for p in pins]
    due = [r for r in adapters if r['status'] != 'ok']
    lines += ['', f'{len(due)} of {len(adapters)} adapters need a refresh.' if due
              else f'All {len(adapters)} adapters are inside the refresh window.']
    return '\n'.join(lines) + '\n'


ISSUE_BODY = """Opened by the weekly adapter drift check: {reasons}.

Re-verify the **{stack}** adapter of `{skill}` against the current official docs.

## Files

- `skills/{skill}/references/adapters.md`, the **{stack}** section
- `skills/{skill}/SKILL.md`, the **{stack}** entry under `## Adapters`, including its stamp line

## Done when

- [ ] Every claim re-checked against official docs, API schema, or source, with a source per claim
- [ ] Pinned version and verification date updated in the prose and the stamp, even if nothing else changed
- [ ] `python scripts/validate.py` passes

See [CONTRIBUTING.md](https://github.com/mahimailabs/voice-ai-skills/blob/main/CONTRIBUTING.md#refreshing-an-adapter). Comment here to pick it up.
"""


def open_issues(adapters: list[dict]) -> None:
    for row in (r for r in adapters if r['status'] != 'ok'):
        title = f"Adapter refresh: {row['skill']} / {row['stack']}"
        found = subprocess.run(['gh', 'issue', 'list', '--state', 'open', '--search', f'"{title}" in:title',
                                '--json', 'title'], capture_output=True, text=True, check=True)
        if any(issue['title'] == title for issue in json.loads(found.stdout)):
            print(f'open already: {title}')
            continue
        body = ISSUE_BODY.format(reasons='; '.join(row['reasons']) or 'stale', **row)
        subprocess.run(['gh', 'issue', 'create', '--title', title, '--body', body,
                        '--label', 'adapter', '--label', 'good first issue', '--label', 'help wanted'], check=True)
        print(f'opened: {title}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--summary', type=Path, help='append the report to this file')
    parser.add_argument('--open-issues', action='store_true',
                        help='open a refresh issue per drifted adapter with none open (needs gh)')
    args = parser.parse_args()
    today = dt.date.today()
    adapters, pins = collect()
    packages = {r['package'] for r in adapters if r['pinned'] != 'unversioned'} | {p['package'] for p in pins}
    releases = {package: pypi_releases(package) for package in sorted(packages)}
    assess(adapters, pins, releases, today)
    text = report(adapters, pins, today)
    print(text)
    if args.summary:
        with args.summary.open('a', encoding='utf-8') as handle:
            handle.write(text)
    if args.open_issues:
        open_issues(adapters)
    return 0


if __name__ == '__main__':
    sys.exit(main())

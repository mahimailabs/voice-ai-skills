#!/usr/bin/env python3
"""Exercise the real skills installer in disposable projects; never installs globally."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from validate import check_skill

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ('claude-code', 'codex', 'cursor', 'gemini-cli', 'github-copilot')


def contents(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['copy', 'symlink'], default='copy')
    args = parser.parse_args()
    names = sorted(p.name for p in (ROOT/'skills').iterdir() if p.is_dir())
    for selection in ['*', *names]:
        with tempfile.TemporaryDirectory(prefix='voice-skills-install-') as folder:
            command = ['npx', '--yes', 'skills@1.5.26', 'add', str(ROOT), '--skill', selection,
                       '--agent', *AGENTS, '--yes']
            if args.mode == 'copy':
                command.append('--copy')
            result = subprocess.run(command, cwd=folder, env={**os.environ, 'DISABLE_TELEMETRY': '1'},
                                    capture_output=True, text=True, timeout=180)
            if result.returncode:
                raise RuntimeError(result.stdout[-4000:] + result.stderr[-4000:])
            wanted = names if selection == '*' else [selection]
            # Four clients share the canonical .agents folder. Claude gets its native path.
            for base in ['.agents/skills', '.claude/skills']:
                for name in wanted:
                    installed = Path(folder)/base/name
                    failures = []
                    check_skill(str(installed), failures)
                    if failures:
                        raise RuntimeError('\n'.join(failures))
                    if contents(installed) != contents(ROOT/'skills'/name):
                        raise RuntimeError(f'Incomplete installed contents: {base}/{name}')
                    helper = installed/'scripts/latency_budget.py'
                    if helper.exists():
                        subprocess.run([sys.executable, str(helper), '--shape', 'cascade', '--eot', '700',
                                        '--ttft', '620', '--ttfb', '240', '--e2e', '1560'],
                                       cwd=folder, check=True, capture_output=True)
            print(f'OK: {args.mode} {selection} for {", ".join(AGENTS)}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())

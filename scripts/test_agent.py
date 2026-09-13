#!/usr/bin/env python3
"""Opt-in native-client acceptance capture. Requires a configured noninteractive CLI.

Example shape (replace the runner with your client's documented command):
  python scripts/test_agent.py --agent CLIENT --output /tmp/acceptance -- runner '{prompt}'
The runner executes in an isolated project with these skills installed. Output and
trace are retained for review; a skill-name match is a smoke signal, not a quality pass.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skill', action='append', help='Install only this skill (repeatable)')
    parser.add_argument('--case', action='append', help='Run only this case ID (repeatable)')
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('runner', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    runner = args.runner[1:] if args.runner[:1] == ['--'] else args.runner
    if not runner or not any('{prompt}' in value for value in runner):
        parser.error("provide a native CLI command containing a {prompt} argument")
    args.output.mkdir(parents=True, exist_ok=False)
    cases = json.loads((ROOT/'tests/agents/cases.json').read_text())
    if args.case:
        unknown = set(args.case) - {case['id'] for case in cases}
        if unknown:
            parser.error(f'unknown cases: {sorted(unknown)}')
        cases = [case for case in cases if case['id'] in args.case]
    skills = args.skill or sorted(p.name for p in (ROOT/'skills').iterdir() if p.is_dir())
    for name in skills:
        if name not in {p.name for p in (ROOT/'skills').iterdir() if p.is_dir()}:
            parser.error(f'unknown skill: {name}')
    reports = []
    for case in cases:
        with tempfile.TemporaryDirectory(prefix='voice-native-') as folder:
            base = '.claude/skills' if args.agent == 'claude-code' else '.agents/skills'
            for name in skills:
                shutil.copytree(ROOT/'skills'/name, Path(folder)/base/name,
                                ignore=shutil.ignore_patterns('__pycache__'))
            command = [value.replace('{prompt}', case['prompt']) for value in runner]
            try:
                result = subprocess.run(command, cwd=folder, text=True, capture_output=True, timeout=args.timeout)
                output, error, code = result.stdout, result.stderr, result.returncode
            except subprocess.TimeoutExpired as exc:
                output = exc.stdout or b''
                error = exc.stderr or b''
                output = output.decode(errors='replace') if isinstance(output, bytes) else output
                error = error.decode(errors='replace') if isinstance(error, bytes) else error
                code = 'timeout'
            (args.output/f"{case['id']}.stdout.txt").write_text(output)
            (args.output/f"{case['id']}.stderr.txt").write_text(error)
            reports.append({**case, 'agent': args.agent, 'exit_code': code,
                            'named_expected_skill': case['expected_skill'] in output,
                            'acceptance': 'needs trace and criteria review'})
    (args.output/'results.json').write_text(json.dumps(reports, indent=2)+'\n')
    print(f'Captured {len(reports)} cases. Review results and tool traces in {args.output}.')
    return int(any(report['exit_code'] != 0 for report in reports))


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Opt-in native-client acceptance runs. Requires a configured noninteractive CLI.

Example shape (replace the runner with your client's documented command):
  python scripts/test_agent.py --agent CLIENT --output /tmp/acceptance -- runner '{prompt}'
The runner executes in an isolated project with these skills installed, once per
scenario in tests/scenarios/. With --trace, stdout is parsed as the client's native
trace: the expected skill must be opened with a non-error result, and the final
answer must meet the scenario's required and forbidden patterns. Prose criteria
still need a human read; a skill-name match alone is never a pass.
"""
import argparse
import json
import sys
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import scenarios  # noqa: E402
import traces  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skill', action='append', help='Install only this skill (repeatable)')
    parser.add_argument('--case', action='append', help='Run only this scenario ID (repeatable)')
    parser.add_argument('--trace', choices=sorted(traces.PARSERS),
                        help='Parse stdout as this native trace format and grade it')
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('runner', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    runner = args.runner[1:] if args.runner[:1] == ['--'] else args.runner
    if not runner or not any('{prompt}' in value for value in runner):
        parser.error("provide a native CLI command containing a {prompt} argument")
    args.output.mkdir(parents=True, exist_ok=False)
    cases = scenarios.cases()
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
            (args.output/f"{case['id']}.stdout.txt").write_text(output, encoding='utf-8')
            (args.output/f"{case['id']}.stderr.txt").write_text(error, encoding='utf-8')
            report = {'id': case['id'], 'expected_skill': case['expected_skill'],
                      'criteria': case['criteria'], 'agent': args.agent, 'exit_code': code,
                      'skills_installed': skills}
            if args.trace:
                trace = traces.PARSERS[args.trace](output, set(skills))
                graded = scenarios.grade(case, trace['answer'])
                loaded = case['expected_skill'] in trace['loaded']
                report.update(loaded=trace['loaded'], expected_skill_loaded=loaded, patterns=graded,
                              acceptance=('needs criteria review' if loaded and graded['passed']
                                          and code == 0 else 'fail'))
            else:
                report.update(named_expected_skill=case['expected_skill'] in output,
                              acceptance='needs trace and criteria review')
            reports.append(report)
    (args.output/'results.json').write_text(json.dumps(reports, indent=2)+'\n')
    for report in reports:
        print(f"{report['id']:<24} {report['acceptance']}")
    print(f'Captured {len(reports)} cases. Review results and tool traces in {args.output}.')
    return int(any(report['exit_code'] != 0 or report['acceptance'] == 'fail' for report in reports))


if __name__ == '__main__':
    raise SystemExit(main())

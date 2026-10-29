# Testing

## Required repository checks

```sh
python scripts/validate.py
python -m unittest discover -s tests -v
python -m compileall -q examples/clinic-agent scripts
```

The validator checks metadata, required headings, size, and all Markdown links in
skills and references. A local link escaping its installed skill is an error. Unit
tests copy every skill alone, run the bundled calculator outside the source tree,
and exercise the shared clinic confirmation and timeout rules without providers.

## Adapter drift

```sh
python scripts/adapter_drift.py
```

Reads the stamp under every stack heading in each skill's `## Adapters` section and the
SDK pins in CI, then compares them with PyPI releases. It prints, per skill and stack,
the pin, the latest release, how many releases the pin is behind, and the days since
verification. An adapter is `due` when its stack shipped a newer minor or major release
or it was verified more than 90 days ago, and `stale` after 180 days, as
[the neutrality policy](neutrality.md#keeping-adapters-current) sets. Drift never fails
a build. The weekly `adapter drift` workflow writes the report to its run summary and,
with `--open-issues`, opens an `Adapter refresh: <skill> / <stack>` issue for each due
adapter that has none open. It needs network access; the unit tests do not.

## Real installer checks

With Node.js 22.20+ and network access:

```sh
python scripts/test_installs.py --mode copy
python scripts/test_installs.py --mode symlink
```

Each command runs `skills@1.6.0` for all five named targets, with the full collection
and each of the ten skills separately. Nothing is installed globally. Complete
installed files, links, and helper execution are checked in temporary projects.

CI also runs the official reference validator as a required check:

```sh
uv tool run --from skills-ref==0.1.1 agentskills validate skills/voice-agent-review
```

Repeat that reference check for every skill, as the workflow does.

## SDK contract regressions

Use a separate environment with the versions recorded in [SDK verification](sdk-verification.md):

```sh
uv venv .venv
uv pip install --python .venv/bin/python 'livekit-agents==1.8.1' 'pipecat-ai[daily,deepgram,cartesia,openai,silero]==1.10.0' 'python-dotenv==1.2.4'
.venv/bin/python -m unittest discover -s tests/sdk -v
```

These load the real SDKs with fake backend/speech I/O. They verify guarded playback,
context ordering, authored errors, metric fields, and imports. They are not a live
voice eval suite or a PSTN readiness claim.

## Behavioral scenarios

Every skill has a scenario file in [`tests/scenarios/`](../tests/scenarios/), at least
two scenarios each. A scenario holds:

- `prompt`: what a user would type.
- `required` and `forbidden`: case-insensitive regular expressions the final answer
  must and must not match. Forbidden patterns encode the skill's `## Do not` list.
- `criteria`: what a human reviewer checks that a pattern cannot.
- `examples`: a passing and a failing answer. The unit tests prove the passing one
  meets every pattern and the failing one trips at least one, so a pattern that has
  drifted into matching everything fails CI.

A new skill needs its scenario file before it lands; `tests/test_scenarios.py` fails
otherwise. Patterns are a floor, not a verdict.

## Native coding-agent acceptance

The runner installs the skills into a disposable project, runs each scenario through
the client's own noninteractive CLI, and keeps stdout and stderr. With `--trace` it
parses stdout as that client's native trace and grades it:

- The expected skill must be opened by a tool call with a matching result that is
  not an error and not empty. Naming the skill in the answer does not count.
- The final answer must meet the scenario's `required` and `forbidden` patterns.

A case that clears both is marked `needs criteria review`; anything else is `fail`.
`tests/test_traces.py` exercises both parsers on synthetic records.

Claude Code (verify flags against the current CLI first):

```text
python scripts/test_agent.py --agent claude-code --trace claude --output /tmp/voice-acceptance -- \
  claude -p '{prompt}' --output-format stream-json --verbose \
  --allowedTools Skill Read Glob Grep 'Bash(python3:*)'
```

Codex:

```text
python scripts/test_agent.py --agent codex --trace codex --output /tmp/voice-acceptance -- \
  codex exec --json --skip-git-repo-check '{prompt}'
```

Add `--case ID` to run one scenario and `--skill NAME` to install only some skills.
Also repeat the review scenarios with only `voice-agent-review` installed and browsing
disabled. The runner substitutes the prompt as a process argument, never a shell
command. It consumes model usage. It is opt-in and is not run by ordinary CI.

Record every run in the harness test record in
[compatibility](compatibility.md#harness-test-record): client and version, date,
repository commit, scenarios run, results, and what was not checked.

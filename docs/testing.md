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
uv pip install --python .venv/bin/python 'livekit-agents==1.8.1' 'pipecat-ai[daily,deepgram,cartesia,openai,silero]==1.10.0' python-dotenv
.venv/bin/python -m unittest discover -s tests/sdk -v
```

These load the real SDKs with fake backend/speech I/O. They verify guarded playback,
context ordering, authored errors, metric fields, and imports. They are not a live
voice eval suite or a PSTN readiness claim.

## Native coding-agent acceptance

The five [acceptance cases](../tests/agents/cases.json) cover review routing,
turn-taking, installed helper execution, uncertain writes, and unavailable docs.
Run them in a new project/session using the client's current documented CLI and
capture its tool trace. Record client/model versions, enabled skills, the repository
commit, date, and results. Also repeat the review case with only the review skill
installed and browsing disabled.

An optional runner creates disposable projects and saves stdout/stderr:

```text
python scripts/test_agent.py --agent CLIENT --output /tmp/voice-acceptance -- NATIVE_CLI_ARGUMENTS '{prompt}'
```

Replace the final command with your authenticated client's noninteractive command;
configure its trace-output flag and verify the current CLI syntax first. The runner
substitutes the prompt as a process argument, never a shell command. It can consume
model usage. It is opt-in and is not run by ordinary CI.

A mention of the expected skill is only a smoke signal. A pass requires a trace that
shows actual skill/reference loading and a response meeting every case criterion.
Review helper tool execution, unsupported claims, and missing-evidence handling.
The compatibility matrix currently records native model acceptance as **not run**.

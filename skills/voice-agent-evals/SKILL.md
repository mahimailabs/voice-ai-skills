---
name: voice-agent-evals
description: Test and evaluate a voice agent. Covers what to assert deterministically versus what to judge with an LLM, the eight judge types, scenario files, simulated callers with accents and background noise, audio versus text runs, regression suites in CI, and a pass-rate maturity curve. Use when someone asks how to test my voice agent, before a release, when a prompt change breaks something silently, or when setting an acceptable pass rate.
license: MIT
metadata:
  author: mahimairaja
  version: "0.1.0"
  category: voice-ai
---

# Voice Agent Evals

This skill decides what a voice test asserts, what it judges, and what pass rate lets
the agent ship. It also decides which suite runs per commit and which runs nightly.

## Use this when

- A prompt edit shipped and a booking flow broke with no failing test.
- Someone asks for an acceptable pass rate before a release.
- The suite is text only and callers report cut-offs and talk-over.
- A run is green while callers wait two seconds for the first word.
- You need scenarios for a booking agent and have only the happy path.

## Do not

- Test only with text. Text never catches endpointing, barge-in, or pronunciation.
- Judge what an assertion could check. A judge over a fixed string is a flaky assert.
- Ship on a green run of five scenarios. Five scenarios measure nothing.
- Skip audio simulation because it is slow. Nightly is slow enough.
- Report pass rate without latency from the same run. Green at 2.4 s is a failed run.
- Write scenarios from the happy path only. The failures live in the other nine.
- Judge with the model that runs the agent. It grades its own mistakes as correct.
- Run a suite against live write tools. Mock every tool that books, charges, or sends.

## Assert or judge

**Assert anything with one correct answer. Judge only what is a matter of degree.**

| assert this | judge this |
| --- | --- |
| the confirmation number appears in the final message | the closing sounds like a clinic, not a bot |
| `book_appointment` was called exactly once | the refusal to give clinical advice stays warm |
| the booked slot equals the slot the caller confirmed | the three offered slots were easy to follow |
| `lookup_patient` ran before any write call | the agent recovered on topic after a digression |
| the transcript carries no markdown characters | the apology after a tool failure sounds calm |
| date of birth was collected before slots were offered | the read-back was easy to follow out loud |

A judged check drifts between runs and costs tokens. An asserted check does neither.
Move a check from the right column to the left the moment it has one correct answer.

## The eight judge types

| judge | what it catches |
| --- | --- |
| accuracy | claims not grounded in tool output, and self-contradiction |
| coherence | topic jumps and a structure the caller cannot follow |
| conciseness | verbosity and repetition that cost the caller time |
| handoff | context dropped when the call moves to another agent |
| relevancy | answers that miss what the caller actually asked |
| safety | unauthorized advice, improper disclosure, missed escalation |
| task completion | the stated goal was not reached by the end of the call |
| tool use | wrong tool, wrong arguments, mishandled tool error |

At least one stack ships all eight under these exact names. See Adapters.
Run four on every conversation: task completion, tool use, accuracy, relevancy.
Add safety on any agent that can be asked for medical, legal, or financial advice.

## Custom deterministic judges

A custom judge does not have to call a model. Example: the confirmation number
returned by the write tool appears verbatim in the final agent message.

That is an assertion wearing a judge's clothes. Write it as a judge only because the
harness runs judges over a whole conversation and assertions over a single turn.
It costs zero tokens, never flakes, and gives the same verdict on every run.

## Text runs and audio runs

| run | what only this catches | cost |
| --- | --- | --- |
| text | tool choice, argument accuracy, flow order, refusals | seconds per scenario |
| audio | cut-offs, talk-over, digit errors, the latency the caller heard | real time per scenario |

Ship neither alone. A text-only suite passes an agent that cuts callers off at
"five five five". An audio-only suite is too slow to run on a commit.

Audio degradation is the part a harness usually controls: background noise, a
low-quality microphone, and packet loss. Those three surface most audio regressions.

Accent is usually a property of the persona you write, not a switch the harness gives
you. Do not assume an accent flag exists. Put the accent in the persona text.

## Maturity curve

| pass rate | what it means | what else must be true |
| --- | --- | --- |
| 70% | prototype, internal demo only | no real callers on the line |
| 85% | pilot with real callers | a human fallback on every failure path |
| 95% | production | audio suite green, p95 inside the latency budget |
| 99% | regulated: health, finance, legal | read-back on every write, logs redacted |

Pass rate is measured over the whole suite, never over the happy-path subset.
The suite size sets the resolution: ten scenarios resolve in steps of 10 percent, so
a ten-scenario suite cannot express 95% at all. Reach twenty before claiming
production, and count the scenarios before you quote a bar.

## Latency belongs in the same run

Report pass rate and latency together. A green run at 2.4 s is a failed run.

Record end-to-end latency per turn at p50 and p95 in the same run that reports passes.
Ceilings: 800 ms for a cascade, 500 ms for speech-to-speech, 300 ms for full-duplex.
Measure on the audio suite only. A text run has no end-of-turn delay to report.
The full breakdown lives in the [voice-latency-budget](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-latency-budget/SKILL.md) skill.

## CI wiring

- Text suite on every commit. Keep it under two minutes or engineers route around it.
- Audio suite nightly, and again before every release. Block the release on it.
- Fail the build on a drop larger than one scenario, or on a pass rate below the bar for the current band.
- Store pass rate, p50, and p95 next to the commit hash. Three runs is a trend.
- Re-run a failed scenario twice before filing it. A judge that flips is a bad judge.

## The clinic suite

Ten scenarios for the clinic booking agent live in
[references/scenarios.md](references/scenarios.md). They cover the happy path, the
digit case, the read-back case, the voicemail case, and six failure paths.

Ten scenarios are the floor, not the release gate. They resolve in steps of 10
percent, so this suite gates a pilot at 85% and cannot express the 95% production bar.
The clinic agent books appointments and reads back a confirmation number, so it needs
that production bar, which means growing the suite past twenty first. Every scenario
that reaches `book_appointment` asserts the read-back happened. Mock that tool always.

## Using this skill

Read related skills by name from your installed skills when available. The repository
links are optional deeper guidance; this skill and its bundled references can be used
on their own. If a linked skill is unavailable, continue with the rules here and name
any analysis you could not complete.

Before writing SDK calls, verify the relevant adapter against current official docs
or a docs MCP. If neither is accessible, use supplied version-matched docs or mark the
API detail unverified. Continue vendor-neutral analysis; do not invent a method or
claim an integration was tested. Python is needed only when running a bundled helper.

## Adapters

Full mappings, flags, and per-claim doc URLs: [references/adapters.md](references/adapters.md)

### LiveKit Agents

Pinned to LiveKit Agents 1.8.1, verified 11 September 2026. The eight judge names map
to the eight factories in `livekit.agents.evals`. Text simulation is the default; audio
is a subcommand carrying three degradation flags and no accent flag.
```python
from livekit.agents.evals import JudgeGroup, accuracy_judge, tool_use_judge
judges = JudgeGroup(llm="openai/gpt-4o-mini", judges=[accuracy_judge(), tool_use_judge()])
result = await judges.evaluate(session.history)
assert result.all_passed, result.judgments
```
Docs: https://docs.livekit.io/agents/start/testing/test-framework.md

### Pipecat

Pipecat 1.0 docs, unversioned pages, checked 11 September 2026. No scenario harness or
shipped judge set is confirmed here: verify against current docs before claiming one.
Per-run latency comes from the metrics observer, which you wire yourself.
```python
from pipecat.observers.loggers.metrics_log_observer import MetricsLogObserver
worker = PipelineWorker(pipeline,
    params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    observers=[MetricsLogObserver()])
```
Docs: https://docs.pipecat.ai/pipecat/fundamentals/metrics

### Vapi

Unversioned docs, checked 11 September 2026. Two separate products: Evals (mock
conversations with response and tool-call checks, `POST /eval` and `POST /eval/run`)
and Simulations (an AI tester holds the call, endpoints under `/eval/simulation/`).
A scenario plus a personality forms a simulation; suites group them; a run holds items.
Each simulation needs at least one structured output as its pass condition: name, type,
description, comparator, expected value. Runs go in Chat mode or Voice mode. Voice mode
does not grade pronunciation, pauses, or interruptions, so it is not an audio pass here.
The docs warn that simulations run unmocked tools for real, so mock `book_appointment`.
Docs: https://docs.vapi.ai/observability/simulations-quickstart

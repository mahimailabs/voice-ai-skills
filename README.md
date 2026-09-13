<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/cover-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="docs/cover-light.png">
  <img alt="Voice AI Skills — ten skills for building better voice agents" src="docs/cover-light.png" width="1122">
</picture>

# Voice AI Skills

Engineering judgment for the coding agent building your voice agent.

![skills](https://img.shields.io/badge/skills-10-informational)
[![Agent Skills](https://img.shields.io/badge/format-Agent_Skills-informational)](https://agentskills.io/specification)
[![license](https://img.shields.io/badge/license-MIT-informational)](LICENSE)
[![validate](https://github.com/mahimailabs/voice-ai-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/mahimailabs/voice-ai-skills/actions/workflows/validate.yml)

A pause is not always the end of a turn. A cough should not cancel a reply.
A booking needs a completed read-back and a clear yes before the write.
These ten skills teach your coding agent how to make those decisions, measure the
result, and find the next thing to fix.

The core is vendor-neutral. Versioned adapters connect the rules to LiveKit,
Pipecat, and Vapi. The files use the open **Agent Skills** format, so the engineering
rules can travel between coding agents and voice stacks.

## Install

Use the installer to choose your coding agent and the skills you want:

```sh
npx skills add mahimailabs/voice-ai-skills
```

Install the full collection for your detected agents:

```sh
npx skills add mahimailabs/voice-ai-skills --skill '*'
```

Or start with the review skill:

```sh
npx skills add mahimailabs/voice-ai-skills --skill voice-agent-review
```

Each skill includes its own references and any required helper. Related skills are
optional deeper reading; installing the full collection gives the reviewer more
specific follow-up guidance.

<details>
<summary>Manual installation and Claude Code plugin</summary>

Copy selected folders from `skills/` into your client's supported skills directory.
Keep each folder intact, including `references/` and `scripts/` when present.

| Coding agent | Project directory |
| --- | --- |
| Claude Code | `.claude/skills/` |
| Codex, Cursor, Gemini CLI, GitHub Copilot | `.agents/skills/` |
| Other Agent Skills clients | Their documented skill directory or import flow |

Claude Code also supports this repository as a plugin:

```text
/plugin marketplace add mahimailabs/voice-ai-skills
/plugin install voice-ai@voice-ai-skills
```

</details>

Installation is tested in copy and symlink modes for the five named client targets,
including single-skill installs. Native model discovery and instruction-following
are a separate check. See [compatibility and verification](docs/compatibility.md)
for evidence, requirements, and the acceptance procedure for another agent.

## Try it

In your coding agent, with a voice-agent project open:

> Review my voice agent for production readiness. Give me the score, hard failures,
> and the three fixes to do first, with file references.

Or bring a concrete symptom:

> Our agent cuts callers off while they read a phone number. Inspect turn-taking
> and interruption handling, and show me what to measure before changing defaults.

If your client does not select skills automatically, explicitly ask it to use
`voice-agent-review` or the relevant skill below.

## The skills

| Skill | What it decides | Use when |
| --- | --- | --- |
| [voice-pipeline-choice](skills/voice-pipeline-choice/) | Cascade, speech-to-speech, half-cascade, or full-duplex, and what each one costs you. | Starting an agent, or someone asks whether to use the realtime API. |
| [voice-turn-taking](skills/voice-turn-taking/) | When the caller has actually finished speaking. | The agent talks over callers, waits too long, or cuts off a phone number. |
| [voice-interruptions](skills/voice-interruptions/) | What stops the agent, and what must never be stopped. | It stops for a cough, ignores a real interruption, or loses a confirmation. |
| [voice-latency-budget](skills/voice-latency-budget/) | Where the milliseconds go and which one to fix first. | The agent feels slow, or you are choosing regions and providers. |
| [voice-prompting](skills/voice-prompting/) | How to write a prompt for a thing that speaks. | The agent reads markdown aloud, or the TTS mangles dates and numbers. |
| [voice-function-tools](skills/voice-function-tools/) | Tool shape, confirmation, timeouts, and filler. | Adding a tool, or tool calls cause dead air and wrong bookings. |
| [voice-telephony](skills/voice-telephony/) | SIP, answering machines, DTMF, transfers, narrowband. | Putting the agent on a phone number, or calls hit voicemail. |
| [voice-agent-evals](skills/voice-agent-evals/) | What to assert, what to judge, and what pass rate ships. | Before a release, or when a prompt change breaks something silently. |
| [voice-full-duplex](skills/voice-full-duplex/) | What breaks when the model listens while it speaks. | Moving to a full-duplex model, or it will not stop talking. |
| [voice-agent-review](skills/voice-agent-review/) | A 40-item score across eight areas, and the three fixes to do first. | Someone asks whether a voice agent is production ready. |

## What's inside

Each skill starts with its triggers and a **Do not** list: the mistakes a coding
agent is likely to make. The core explains the tradeoffs, numerical defaults, ranges,
and symptoms. The adapter section and bundled references identify vendor-specific
settings, source links, and verification dates.

SDK APIs drift. Verify adapter details against current official documentation before
writing code. If docs are unavailable, the agent can still apply the core rules and
must label unverified API details. Reading skills needs no SDK or MCP server; the
optional latency calculator needs Python 3.10 or later.

One clinic booking example connects the rules across the collection. Its
[LiveKit and Pipecat implementations](examples/clinic-agent/) share confirmation
state, tool deadlines, filler, and timeout reconciliation. They demonstrate six review
areas and intentionally omit telephony, durable storage, and a voice eval suite.

From a repository checkout, inspect a measured latency budget:

```sh
python scripts/latency_budget.py --shape cascade --eot 700 --ttft 620 --ttfb 240 --e2e 1560
```

When installed separately, the calculator lives inside `voice-latency-budget/scripts/`;
the skill explains how to resolve it from its own directory.

## Contributing

Contributions for more coding agents and voice stacks are welcome. Keep engineering
rules portable, give numerical claims a source or a stated rationale, and record the
version and date for adapter claims. Include installation evidence before expanding
the tested-client matrix.

```sh
python scripts/validate.py
python -m unittest discover -s tests -v
python scripts/test_installs.py --mode copy
python scripts/test_installs.py --mode symlink
```

The installation checks need Node.js 22.20+ and network access. See
[testing](docs/testing.md) for SDK checks and native-agent acceptance cases.

## Related

[livekit/agent-skills](https://github.com/livekit/agent-skills) ·
[VapiAI/skills](https://github.com/VapiAI/skills) ·
[pipecat-ai/skills](https://github.com/pipecat-ai/skills)

Use those for stack-specific APIs and this collection for the decisions around them.

## Author

Mahimai Raja J. [handbook.mahimai.ca](https://handbook.mahimai.ca) ·
[@voicexprt](https://x.com/voicexprt)

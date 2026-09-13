# voice-ai-skills

_The rules of voice agents, written down so your coding agent stops guessing._

![skills](https://img.shields.io/badge/skills-10-informational)
![license](https://img.shields.io/badge/license-MIT-informational)
[![validate](https://github.com/mahimairaja/voice-ai-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/mahimairaja/voice-ai-skills/actions/workflows/validate.yml)

Your coding agent knows how to call a voice SDK. It does not know that 0.5 seconds
of silence is not the end of a turn, that a read-back must not be interruptible, or
that an answering machine sounds like a person for the first two seconds. These
skills teach it that.

## Install

```
npx skills add mahimairaja/voice-ai-skills
```

In Claude Code, as a plugin:

```
/plugin marketplace add mahimairaja/voice-ai-skills
/plugin install voice-ai@voice-ai-skills
```

Or copy the folders you want in by hand. Claude Code reads `.claude/skills/` in the
project and `~/.claude/skills/` globally. Cursor, Codex, Gemini CLI and Copilot read
`.agents/skills/` in the project, which is the cross-client convention.

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

## How they work

Every skill leads with a `## Do not` list, right after its trigger list. That list is
where a coding agent's default behavior is wrong for voice, and it is the highest-
value part of the file. Every rule carries a number, a range, and the symptom you see
when the number is wrong. The body of each skill never names a vendor. The last
section, `## Adapters`, maps the rule onto LiveKit, Pipecat, and Vapi;
`references/adapters.md` carries a doc link per claim and the version it was checked
against. One running example, a clinic appointment booking agent, appears in all ten,
so the rules compose instead of contradicting.

`python scripts/latency_budget.py --shape cascade --eot 700 --ttft 620 --ttfb 240 --e2e 1560`
prints where a measured turn is over budget and which stage to fix first.

## Try it

With the skills installed, open Claude Code in a voice agent repo and type: _review my
voice agent_. You get a score out of 40 and three fixes, each naming a file.

## Related

[livekit/agent-skills](https://github.com/livekit/agent-skills) ·
[VapiAI/skills](https://github.com/VapiAI/skills) ·
[pipecat-ai/skills](https://github.com/pipecat-ai/skills)

Use those for the API. Use this for the judgment.

## Contributing

Adapter PRs are welcome, especially for stacks not covered here. Every number needs
a doc link, every vendor claim needs the version and date it was checked against,
and the vendor-neutral core of a skill stays vendor-neutral. Run
`python scripts/validate.py` before you open the PR.

## Author

Mahimai Raja J. [handbook.mahimai.ca](https://handbook.mahimai.ca) ·
[@mahimairaja](https://x.com/mahimairaja)

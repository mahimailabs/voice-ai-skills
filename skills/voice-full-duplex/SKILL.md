---
name: voice-full-duplex
description: Build on full-duplex speech models that listen while they speak. Covers what breaks compared with turn-based models, including no turn detector, no forced stop, tools delegated to a backend model, no verbatim script, no text-only mode, append-only context after startup, side channels, and cost accounting. Use when moving to GPT-Live or another model that listens while it speaks, when a full-duplex model will not stop talking and no cancel call works, when tools never fire, or when say() raises.
license: MIT
metadata:
  author: mahimairaja
  version: "0.1.0"
  category: voice-ai
---

# Voice Full Duplex

A full-duplex model holds both audio directions open and decides for itself when to
speak. Adopting one deletes your turn-taking layer, and five habits with it.

## Use this when

- Moving an agent from a turn-based pipeline to a model that listens while it speaks.
- The model keeps talking after the caller interrupts, and nothing you call stops it.
- Tool calls never fire, even though the tools are registered and the persona names them.
- say() raises, or a string you needed spoken word for word comes out re-worded.
- Context edits after startup have no effect and no error appears in the logs.

## Do not

- Do not pass a turn detector. The model owns turn boundaries and your detector changes nothing.
- Do not expect say() to work. There is no verbatim path, so it raises or gets talked over.
- Do not put tool instructions in the voice persona. The voice model never sees the tools.
- Do not expect a string read back verbatim. Numbers are re-spoken in the model's own words.
- Do not rebuild context after startup. History is append-only and edits are dropped in silence.
- Do not change persona mid-call. A new persona needs a new connection and a fresh startup history.
- Do not assume an interrupted response can be truncated. The model still holds the whole turn.
- Do not drop the VAD. Without one, playback runs until the model stops on its own.

## What changes

Both directions are open at once. The model hears the caller while it is speaking,
and it starts, pauses, and stops on its own judgment of the conversation. Nothing you
send creates, cancels, or truncates a response. Your endpointing delays, your
interruption thresholds, and your backchannel filters are now dead weight. They still
parse and they still log. They change nothing about when the agent speaks. What you
keep is the audio path, the persona, the tools, and the cut on your playback buffer.

## The five rules that break

1. The model will not stop talking. No client call cancels or truncates a response.
2. Tools never fire. The voice model never sees them, so a backend model owns them.
3. say() raises. The duplex connection carries no verbatim speech path.
4. The script is paraphrased. Every string you write becomes the model's own wording.
5. Context edits are silently dropped. After startup the history is append-only.

Symptom, cause, and fix for each: [references/gpt-live-rules.md](references/gpt-live-rules.md).

## The talker and the thinker

Two models run one call. The voice model talks: it hears the caller, holds the
persona, decides when to speak, and produces the audio. It carries no tools and no
reasoning budget. A backend text model thinks. It reads the open turn, picks the
tools, and returns an answer. The voice model then speaks that answer in its own words. Your
function tools still run in your own process, and each result goes back to the
backend model, never to the voice model.

Write the delegation as one sentence in the persona. Say which requests to hand off
and which to answer directly. Never describe the tools themselves.

A delegated turn pays the backend model's time to first token. Budget 700 ms for it.
Speech the voice model produces on its own has an end-to-end ceiling of 300 ms.

## A VAD is still required

Keep a voice activity detector in the session. The model decides when it stops
speaking, but it does not drain the audio already queued on your side.

Playback is cut by your own interruption detection, and that path needs a VAD.
Without one the agent keeps playing seconds after the caller started talking.

## Context is append-only after startup

The history you pass before the connection opens is the startup budget: 128 messages
or 8192 rendered tokens, whichever binds first. Over the limit, the oldest messages
drop. After the session starts, the history is append-only.

| move | allowed after startup | what happens if you try |
| --- | --- | --- |
| append a new message | yes | it reaches the model |
| rebuild the context from a store | no | the edit is dropped, the original stands |
| summarize turns in place | no | the edit is dropped, the original stands |
| swap the system prompt | no | the original persona keeps running |
| truncate an interrupted reply | no | the model keeps a turn the caller never heard |

The last row is the one that bites. The caller hears half a sentence. The model holds
all of it, and later in the call it refers back to words that were never played.

## The three side channels

Appends are capped at 500 tokens each. They do not enter the session transcript.

| channel | what belongs in it |
| --- | --- |
| standing instruction | a rule that applies for the rest of the call |
| silent context | a fact the model uses only if it becomes relevant |
| speak now | something to say immediately, phrased by the model |

Asking for a reply is a request, not a command. The model may refuse a reply that
does not fit the conversation. If it has not started speaking 10 s after the request,
treat the reply as declined and check the handle for the failure.

## Cost

The voice model lists at 0.05 USD per minute, plus backend model tokens: re-check
current pricing before any decision rests on it.

Two meters, not one. Session seconds bill whether or not the model is speaking, and
every delegated turn adds tokens on top. Record the two separately, or a bill that
doubles will not tell you which half moved. A chatty persona raises seconds; a
tool-heavy flow raises tokens. They are fixed by different changes.

## The clinic verdict

Riverside Family Medicine should not move to full-duplex.

The agent reads back "Tuesday the fourteenth at three fifteen with Doctor Osei" and
then a confirmation number. A full-duplex model re-words both, on every call. No
read-back gate holds it: there is no way to force the exact string or to make a
segment uninterruptible. The failure is silent: the booking is right, the
spoken confirmation number is wrong, and the caller writes down what they heard.

What would change the verdict:

- The confirmation number leaves speech. The caller reads it in a text message, and
  nothing spoken has to be exact.
- A verbatim path lands on the duplex connection, so a supplied string is spoken as
  written rather than re-phrased.
- Truncation of an interrupted reply lands, so the model's history matches what the
  caller actually heard.

Until then, keep the cascade. See [voice-pipeline-choice](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-pipeline-choice/SKILL.md) for the shape decision and
[voice-interruptions](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-interruptions/SKILL.md) for the read-back gate this model cannot honor.

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
Pinned: LiveKit Agents 1.8.x, Pipecat 1.0 and Vapi unversioned, checked 11 September
2026. Only one stack ships a full-duplex model today, so it carries the detail here.
Full mappings and every source URL: [references/adapters.md](references/adapters.md).

### LiveKit Agents
Pass `GPTLiveModel` as `llm`, and pass a VAD: the session drops its default one here.
Instructions go on the `Agent`. Startup context: 128 messages or 8192 tokens. The three
channels `append_instructions`, `append_thinking`, `append_commentary` take 500 tokens each.
```python
from livekit.agents import AgentSession, inference
from livekit.plugins.openai.realtime import GPTLiveModel
session = AgentSession(vad=inference.VAD(model="silero"), llm=GPTLiveModel(
    voice="marin", responses_options={"model": "gpt-5.6-luna"}))
```
Docs: https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/

### Pipecat
No full-duplex service class in the 1.0 pages checked: verify against current docs.
Docs: https://docs.pipecat.ai/pipecat/learn/your-first-agent

### Vapi
A turn-based speech-to-speech block, not a full-duplex one. Turn control stays in
`startSpeakingPlan` and `stopSpeakingPlan`. Full-duplex: verify against current docs.
Docs: https://docs.vapi.ai/openai-realtime

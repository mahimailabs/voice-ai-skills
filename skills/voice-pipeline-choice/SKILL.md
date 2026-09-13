---
name: voice-pipeline-choice
description: Choose the pipeline shape for a voice agent, whether cascaded STT-LLM-TTS, a speech-to-speech realtime model, a half-cascade (realtime model in text mode plus a separate TTS), or full-duplex. Covers what each shape gives up on exact wording, latency, prosody, and cost per minute. Use when starting a voice agent or choosing its architecture, when someone asks whether to use the realtime API or speech-to-speech, when a speech-to-speech model paraphrases a number, date, or confirmation code that must be said exactly, or when latency, voice control, or cost is the deciding factor.
license: MIT
metadata:
  author: mahimairaja
  version: "0.1.0"
  category: voice-ai
---

# Voice Pipeline Choice

Pick the shape of the audio path before writing agent code. The shape decides what
you can control: the exact words, the delay, the voice, and the bill.

## Use this when

- Starting a voice agent and choosing the audio path for the first time.
- Someone proposes a speech-to-speech model on the grounds that it is newer.
- The agent must say a date, a time, or a confirmation number exactly.
- Perceived latency sits above 800 ms and you suspect the shape, not the tuning.
- Cost per minute is the binding constraint at your call volume.

## Do not

- Do not default to speech-to-speech because it is newer. Newer buys prosody, not wording control.
- Do not assume a realtime model will read a string verbatim. It paraphrases, including numbers.
- Do not assume a cascade is always slower. A tuned cascade lands at 800 ms end to end.
- Do not pick a shape before you know whether exact wording is required. That one answer removes two shapes.
- Do not treat the shape as permanent. It is a config boundary you can cross later.
- Do not choose on a demo. Choose on a phone call, on the narrowband path your callers use.
- Do not mix shapes inside one turn to get both. You inherit the failure modes of both.

## The four shapes

- Cascade: STT, then LLM, then TTS, as three services you own and can swap.
- Speech-to-speech: audio in, audio out, one model, one hop, turns still yours.
- Half-cascade: a realtime model emits text, your own TTS speaks that text.
- Full-duplex: both directions open at once, and the model decides when to speak.

```
cascade            mic ──> STT ──> LLM ──> TTS ──> speaker
                           exact words, cheapest, four places to lose time

speech-to-speech   mic ──────────> realtime model ──────────> speaker
                           one hop, best prosody, no control of wording

half-cascade       mic ──────> realtime model ──> TTS ──> speaker
                                  (text out)     your voice, your words

full-duplex        mic ═══════> full-duplex model ═══════> speaker
                   <════ both directions open at the same time ════>
                           it can speak while the caller speaks
```

## Decision table

| requirement | shape to pick | what you give up |
| --- | --- | --- |
| Exact wording of numbers, dates, and codes | cascade, or half-cascade | one extra hop, and the joint prosody of a single model |
| Lowest perceived latency | full-duplex, else speech-to-speech | wording control, and the ability to force a stop |
| Most natural prosody | speech-to-speech | the exact string, and voice portability |
| Cost at scale | cascade | integration and tuning work across three stages |
| Talking over the caller (interjections, "one moment") | full-duplex | turn control, verbatim output, and any text-only mode |
| Swapping a provider without a rewrite | cascade | joint prosody, and per-stage tuning becomes your job |
| Strict voice or brand control | cascade, or half-cascade | the output prosody of a single joint model |
| Running inside a regulated data boundary | cascade | one vendor's convenience: you now place three services |

Full matrix across ten dimensions: [references/defaults.md](references/defaults.md).

## What each shape gives up

Cascade gives up prosody across a sentence boundary. The TTS never heard the caller,
so it cannot match energy or pace, and emphasis has to be written in. It also gives
up one hop of time: four places to lose milliseconds instead of one.

Speech-to-speech gives up the exact string. The model rephrases, and it rephrases
numbers, so a confirmation code comes out sounding different every call. It also
gives up voice portability, because the voice belongs to the model vendor.

Half-cascade gives up most of the prosody advantage it was meant to keep. Text leaves
the realtime model, so the TTS speaks it cold, exactly as in a cascade. It buys
audio-native understanding and keeps your voice, and it pays audio-input prices.

Full-duplex gives up control of the turn. No detector, no forced stop, no verbatim
script, and an interrupted response stays whole in the model's context. It buys
overlap: the agent can say "one moment" while the caller is still speaking.

## Cost per minute

Order of magnitude only. Re-check current pricing before any decision rests on it.

| shape | order of magnitude, per minute | what drives the number |
| --- | --- | --- |
| cascade | cents, low single digits | three metered stages, each billed separately |
| half-cascade | cascade, plus audio input on the realtime model | audio tokens in, text tokens out, plus TTS characters |
| speech-to-speech | a small multiple of a cascade | audio tokens in and audio tokens out |
| full-duplex | 0.05 USD list for the voice model, plus backend model tokens | session seconds, plus every delegated token |

Re-check current pricing. Rates move each quarter, and the cheapest shape inverts.
Cost only decides the shape above roughly ten thousand minutes a month. Below that,
wording control and latency decide it, and the cost difference is rounding.

## The clinic decision

Riverside Family Medicine runs a cascade.

It reads back "Tuesday the fourteenth at three fifteen with Doctor Osei" and a
confirmation number, and both must be exact. A paraphrase there books the wrong slot.

## When to change your mind

- Read-backs stop mattering. No number the caller must act on is spoken any more, so
  the wording constraint is gone and speech-to-speech is open.
- Measured p50 stays above 800 ms after the whole order of fixes in
  [voice-latency-budget](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-latency-budget/SKILL.md). The shape is now the ceiling, not the tuning.
- Transcripts show callers expecting overlap, not turns. They interject, the agent
  waits, and the call stalls. Evaluate full-duplex against [voice-full-duplex](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-full-duplex/SKILL.md).

Re-measure after any change, on a real phone call. See [voice-latency-budget](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-latency-budget/SKILL.md) for the
measurement rules and [voice-turn-taking](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-turn-taking/SKILL.md) for what the shape hands you to tune.

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

Pinned: LiveKit Agents 1.8.x, verified 11 September 2026. Pipecat 1.0 docs and Vapi
unversioned docs, checked 11 September 2026. Re-verify every identifier before use.
Full mappings: [references/adapters.md](references/adapters.md).

### LiveKit Agents

Cascade: pass stt, llm and tts. For speech-to-speech, pass a realtime model as llm.

```python
session = AgentSession(stt="deepgram/nova-3", llm="google/gemma-4-31b-it",
                       tts="inworld/inworld-tts-2")
```
No half-cascade with GPT-Live: it has no text-only response modality.
Docs: https://docs.livekit.io/agents/start/voice-ai/

### Pipecat

Cascade: an ordered Pipeline list. The canonical order is transport.input(), stt,
aggregators.user(), llm, tts, transport.output(), aggregators.assistant().
Ordering is load-bearing. The assistant aggregator must follow transport.output(),
so only text that was actually spoken reaches the context.
In 1.0 the runnable object is PipelineWorker; PipelineTask is a deprecated alias.
Speech-to-speech and full-duplex service classes: verify against current docs.
Docs: https://docs.pipecat.ai/pipecat/learn/your-first-agent

### Vapi

Cascade: set three blocks on the assistant, transcriber, model and voice.
Speech-to-speech: keep one model block with provider openai and a realtime model id.
The production realtime id is gpt-realtime-2025-08-28. Vapi's own docs describe the
three-block form as orchestration that simulates speech-to-speech.
Realtime models accept only alloy, echo, shimmer, marin and cedar as voices.
That voice list is the brand-control cost, stated as a config limit.
Docs: https://docs.vapi.ai/openai-realtime

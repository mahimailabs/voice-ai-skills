---
name: voice-latency-budget
description: Build, measure, and fix a latency budget for a voice agent. Covers the five timings that matter (transcription delay, end-of-turn delay, LLM time to first token or TTFT, TTS time to first byte or TTFB, end to end), targets per pipeline shape, where the milliseconds hide, and the order to fix them in. Use when the agent feels slow or laggy, when choosing regions or providers, when reading latency metrics, or when someone asks what good latency is.
license: MIT
metadata:
  author: mahimairaja
  version: "0.1.0"
  category: voice-ai
---

# Voice Latency Budget

This skill sets what each stage of a voice turn is allowed to cost. It also decides
which stage to fix first when the total is over. The target is under 800 ms from the
caller's last word to the first agent audio.

## Use this when

- A caller says the agent feels slow, and every provider dashboard is green.
- You have one latency number and no idea which stage owns it.
- You are picking a region, a provider, or a model size on latency grounds.
- A turn that calls a tool feels twice as slow as a turn that does not.
- Someone asks what good latency is for a phone agent.

## Do not

- Report one latency number. Report p50 and p95 per stage, or you reported nothing.
- Measure from a laptop on Wi-Fi and call it production. Measure on a real phone call.
- Optimize the LLM before the endpointing delay. Endpointing is usually the bigger number.
- Split the LLM and the TTS across regions. Each cross-region hop costs 80 to 150 ms.
- Forget the end-of-turn delay. The caller feels it and your model metrics exclude it.
- Average turns that call a tool together with turns that do not. Bucket them apart.
- Tune against p50 only. The p95 turn is the one the caller complains about.

## The five timings

| timing | starts when | stops when |
| --- | --- | --- |
| transcription delay | the caller's speech ends | the final transcript is available |
| end-of-turn delay | the caller's speech ends | the turn is declared finished |
| LLM time to first token | the turn is handed to the model | the first token comes back |
| TTS time to first byte | the first text token reaches synthesis | the first audio chunk comes back |
| end to end | the caller's last word | the first agent audio reaches the caller |

Only the last one is what the caller experiences. The other four explain it.

## What the caller feels

The caller feels the end-of-turn delay plus everything after it. Transcription
usually runs inside the end-of-turn window on a streaming stack, so it rarely adds to
the total. Model and synthesis timers start only after the turn is declared over.
That is why a green model dashboard and a slow-feeling agent are the normal case.

The endpointing delay is usually the largest single number in the budget. At the
default of 0.5 s it is 500 ms of an 800 ms ceiling before the model has seen a token.
Measure it first. Fix it first.

## Budget by shape

Values are p50 milliseconds on a real phone call. p95 ceilings are in
[references/defaults.md](references/defaults.md).

| stage | cascade | speech-to-speech | full-duplex |
| --- | --- | --- | --- |
| end-of-turn delay | 300 to 500 | 300 | not applicable |
| transcription delay | 100 to 200 | folded into the model | folded into the model |
| LLM time to first token | 200 to 400 | folded into the model | 700 for the delegated backend model |
| TTS time to first byte | 100 to 300 | folded into the model | folded into the model |
| end to end, ceiling | 800 | 500 | 300 |

A speech-to-speech shape gives you one number to tune and four you cannot see. A
full-duplex shape has no end-of-turn delay, because the model decides when to speak.
Its backend model thinks behind the voice, so 700 ms there is not heard as a gap.

## Where the milliseconds hide

- Cross-region hops: 80 to 150 ms per round trip between continents, on every stage.
- Cold synthesis connection: 200 to 400 ms on the first utterance only. Warm it at answer.
- Non-streaming synthesis: the whole reply renders before the first byte, 300 to 900 ms.
- Prompt size: each extra 10,000 tokens of prompt costs 100 to 300 ms of time to first token.
- Tool round trip: 200 to 1500 ms, and it lands inside the turn, not beside it.
- Jitter buffer and codec on a phone call: 40 to 100 ms each way, absent from your metrics.

These are starting estimates, not measurements. Measure each on your own stack before
you budget against it. The per-item table is in
[references/defaults.md](references/defaults.md).

## The order of fixes

Apply in this order. Stop as soon as you are inside budget.

1. Endpointing. Cut the min delay to the floor your caller types tolerate. Gain 200 to 400 ms.
2. Preemptive generation. Start the model on the partial transcript. Gain 200 to 300 ms.
3. Streaming TTS. Speak the first sentence while the rest renders. Gain 200 to 600 ms.
4. Region co-location. Put every hop in one region. Gain 80 to 150 ms per hop removed.
5. Smaller model. Gain 100 to 300 ms of time to first token, at a cost in accuracy.

Do not reorder this list. Steps 1 through 4 cost nothing in answer quality, though
each carries its own risk, priced per step in references/defaults.md. Step 5 is the
only one that trades answer quality for milliseconds, so it goes last, with an eval run.

## The budget script

[`../../scripts/latency_budget.py`](../../scripts/latency_budget.py) scores measured
timings against the ceiling for one shape and names the stage to fix first. Every
flag takes milliseconds. At least one measurement is required. Stages folded into the
model for that shape print as not applicable and are not scored.

Run it as: `python scripts/latency_budget.py --shape cascade --eot 700 --stt 150
--ttft 620 --ttfb 240 --e2e 1560`. Shapes are `cascade`, `s2s`, and `full-duplex`.

The output is one row per stage carrying the measurement, the ceiling, and either
`ok` or the overrun in milliseconds. Below the rows it prints the worst stage, the
stage to fix first, and the one-line fix for it. When the two differ it says so,
because the cheapest fix often moves the worst stage as a side effect.

## How to measure

- Report p50 and p95 for every stage. A single number hides the turn that lost the caller.
- Use at least 50 turns. Below 50 turns, p95 is one sample with a label on it.
- Measure on a real phone call. Wi-Fi from a laptop under-reports jitter buffer and codec.
- Bucket turns with a tool call apart from turns without. Mixing them hides both.
- Log per-turn timings against a turn id, so a slow p95 turn can be pulled and replayed.
- Re-measure after every fix. Fixes interact: cutting endpointing exposes a slow model.

A run that reports pass rate without latency in the same run is not a passing run.
Measure both together.

## The clinic call

Riverside Family Medicine runs a cascade agent on the main line for booking. Measured
over 80 inbound PSTN turns, p50 end to end was 1560 ms against an 800 ms ceiling.

| stage | measured p50 | ceiling | verdict |
| --- | --- | --- | --- |
| end-of-turn delay | 700 | 500 | over by 200 |
| transcription delay | 150 | 200 | inside budget |
| LLM time to first token | 620 | 400 | over by 220 |
| TTS time to first byte | 240 | 300 | inside budget |
| end to end | 1560 | 800 | over by 760 |

Transcription ran inside the end-of-turn window, so the three visible stages summed to
the total: 700 plus 620 plus 240.

Time to first token was the worst single overrun. Endpointing was still fixed first,
because it is step 1 and it is free. The min delay had been raised to 0.8 s to stop
the agent cutting off callers reading a date of birth. An audio turn detector replaced
that guess, at min 0.3 s and max 2.5 s, and end-of-turn delay fell to 320 ms. The
digit case still passed. Preemptive generation then took time to first token to 360 ms.
Co-locating synthesis with the agent took time to first byte to 110 ms. p50 landed at
790 ms. A smaller model was never needed.

## Adapters

Vendor names appear only here and in
[references/adapters.md](references/adapters.md).

### LiveKit Agents

- Pinned: LiveKit Agents 1.8.x for Python, verified 11 September 2026.
- Read per-turn latency from `ChatMessage.metrics`. `metrics_collected` is deprecated.
- Keys: `transcription_delay`, `end_of_turn_delay`, `llm_node_ttft`, `tts_node_ttfb`, `e2e_latency`.
- `MetricsReport` is a `TypedDict(total=False)`, so read every key with `.get()`.
- `llm_node_ttft` and `tts_node_ttfb` are said to be cascade-only: verify against current docs.
- Preemptive generation: `turn_handling["preemptive_generation"]`, `enabled` True, `preemptive_tts` False.
- Endpointing: `turn_handling["endpointing"]`, `min_delay` 0.5, `max_delay` 3.0.
- Docs: https://docs.livekit.io/deploy/observability/data/

### Pipecat

- Pinned: Pipecat 1.0, unversioned docs, checked 11 September 2026.
- Metrics are off by default. Set `enable_metrics=True` and `enable_usage_metrics=True`.
- Logged: TTFB, TTFA (TTS only), TTFAT (LLM only), Processing Time, Text Aggregation.
- `report_only_initial_ttfb` defaults to False, so TTFB is reported per utterance.
- Read them with `MetricsLogObserver`, passed to the worker in `observers=[...]`.
- No documented end-to-end turn figure. `TurnMetricsData` exists: verify against current docs.
- Docs: https://docs.pipecat.ai/pipecat/fundamentals/metrics

### Vapi

- Pinned: unversioned rolling API, checked 11 September 2026.
- `startSpeakingPlan.waitSeconds` is the reply floor: default 0.4, min 0, max 5.
- Pipeline latency pushes past that minimum. The knob cannot make the rest faster.
- Precedence: `customEndpointingRules`, `smartEndpointingPlan`, `transcriptionEndpointingPlan`, built-in.
- `transcriptionEndpointingPlan`: `onPunctuationSeconds` 0.1, `onNoPunctuationSeconds` 1.5.
- `onNumberSeconds` is contradictory in the spec: prose says 0.4, annotation says 0.5.
- The LiveKit smart endpointing `waitFunction` default is `200 + 8000 * x`: 200 to 8200 ms.
- No per-stage latency breakdown in the verified fact set: verify against current docs.
- Docs: https://docs.vapi.ai/customization/speech-configuration

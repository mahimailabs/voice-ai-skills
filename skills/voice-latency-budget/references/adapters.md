# Latency adapters

Where each stack exposes the five timings, what it calls them, and which knob moves
each one. Every claim carries the doc URL it came from.

## LiveKit Agents

Pinned: LiveKit Agents 1.8.x for Python (1.8.1 seen on PyPI), verified
11 September 2026.

### Metric names

`ChatMessage.metrics` is a `MetricsReport`, a `TypedDict(total=False)`. Every key is
optional, so read with `.get()`.

| this skill | LiveKit key | role it appears on |
| --- | --- | --- |
| transcription delay | `transcription_delay` | user message |
| end-of-turn delay | `end_of_turn_delay` | user message |
| LLM time to first token | `llm_node_ttft` | assistant message |
| TTS time to first byte | `tts_node_ttfb` | assistant message |
| end to end | `e2e_latency` | assistant message |

Other keys on the same report: `started_speaking_at`, `stopped_speaking_at`,
`on_user_turn_completed_delay`, `llm_node_tps`, `llm_node_ttfs`, `playback_latency`,
`provider_request_ids`.

Definitions, verbatim in substance: `transcription_delay` is the time to obtain the
transcript after the end of the user's speech. `end_of_turn_delay` is the time between
end of speech and the decision to end the user's turn. `llm_node_ttft` is the time for
the `llm_node` to return the first token. `tts_node_ttfb` is the time for the
`tts_node` to return the first chunk of audio after the first text token was sent.
`e2e_latency` is the time from when the user finished speaking to when the agent began
responding.
Source: https://docs.livekit.io/deploy/observability/data/

`llm_node_ttft` and `tts_node_ttfb` are reported to be populated by the cascade only,
and empty on a realtime model. That claim is not confirmed on a docs page:
verify against current docs.
Source: https://docs.livekit.io/deploy/observability/data/

The session-level `metrics_collected` event is deprecated. Use `session_usage_updated`
for usage and `ChatMessage.metrics` for per-turn latency.
Source: https://docs.livekit.io/deploy/observability/data/

### Reading per-turn latency

Source: https://docs.livekit.io/deploy/observability/data/

```python
from livekit.agents import ConversationItemAddedEvent
from livekit.agents.llm import ChatMessage

@session.on("conversation_item_added")
def on_conversation_item_added(ev: ConversationItemAddedEvent):
    if not isinstance(ev.item, ChatMessage):
        return
    m = ev.item.metrics
    if ev.item.role == "assistant" and m.get("e2e_latency") is not None:
        print(f"E2E latency: {m['e2e_latency']:.3f}s")
```

### Fix 1, endpointing

Endpointing lives at `turn_handling["endpointing"]`. `EndpointingOptions` keys:
`mode` ("fixed" or "dynamic", default "fixed"), `min_delay` (0.5), `max_delay` (3.0),
`alpha` (0.9, dynamic only). With a streaming turn detector, unspecified keys fall
back to `min_delay` 0.3 and `max_delay` 2.5.

The AgentSession kwargs `min_endpointing_delay` and `max_endpointing_delay` are
deprecated in 1.8.x. Passing `turn_handling` alongside a legacy kwarg silently
discards the legacy kwarg. Never mix the two styles.
Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/agent_session.py

```python
from livekit.agents import AgentSession, TurnHandlingOptions, inference

session = AgentSession(
    turn_handling=TurnHandlingOptions(
        turn_detection=inference.TurnDetector(),
        endpointing={"min_delay": 0.3, "max_delay": 2.5},
        preemptive_generation={"enabled": True, "preemptive_tts": True},
    ),
)
```

### Fix 2, preemptive generation

`PreemptiveGenerationOptions` lives at `turn_handling["preemptive_generation"]`, not
as an AgentSession kwarg. Keys and defaults: `enabled` True, `preemptive_tts` False,
`max_speech_duration` 10.0, `max_retries` 3. Turning on `preemptive_tts` also starts
synthesis early, which is fix 2 and fix 3 in one switch.
Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/turn.py

### Measuring a suite

`lk agent simulate audio` reports the end-to-end latency the caller heard at p50, p95,
and p99, where a negative value means the agent talked over the caller. It breaks the
turn down by stage: transcription and endpointing delay, LLM time to first token and
time to first sentence, tokens per second, and TTS time to first byte. Text mode is
the default and disables audio entirely, so it measures no latency worth reporting.
Source: https://docs.livekit.io/agents/start/testing/simulations.md

## Pipecat

Pinned: Pipecat 1.0. The docs are unversioned, checked 11 September 2026.

Metrics are off by default. Set both flags on `PipelineParams` before measuring.
`enable_metrics=True` logs five metrics: TTFB (time to first byte, seconds), TTFA
(time to first audio, TTS services only), TTFAT (time to first answer token, LLM
services only), Processing Time, and Text Aggregation (first LLM token to first
complete sentence, TTS only). `enable_usage_metrics=True` adds LLM token usage and
TTS character usage, per interaction rather than as running totals.
`report_only_initial_ttfb` defaults to False.
Source: https://docs.pipecat.ai/pipecat/fundamentals/metrics

Source: https://docs.pipecat.ai/pipecat/fundamentals/metrics

```python
from pipecat.observers.loggers.metrics_log_observer import MetricsLogObserver

worker = PipelineWorker(
    pipeline,
    params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    observers=[MetricsLogObserver()],
)
```

Metrics arrive as a `MetricsFrame` (`from pipecat.frames.frames import MetricsFrame`)
per interaction. `frame.data` is a list of objects from `pipecat.metrics.metrics`:
`TTFBMetricsData`, `TTFAMetricsData`, `TTFATMetricsData`, `ProcessingMetricsData`,
`LLMUsageMetricsData`, `STTUsageMetricsData`, `TTSUsageMetricsData`,
`TextAggregationMetricsData`, `TurnMetricsData`. Filter with
`MetricsLogObserver(include_metrics={LLMUsageMetricsData, TTSUsageMetricsData})`.
Source: https://docs.pipecat.ai/pipecat/fundamentals/metrics

A single end-to-end turn latency figure is not documented on the metrics page. A
`TurnMetricsData` class exists in the same module, and `PipelineWorker` takes
`enable_turn_tracking=True` by default, but the field set is not confirmed:
verify against current docs.
Source: https://docs.pipecat.ai/pipecat/fundamentals/metrics

Endpointing sits in `VADParams` on the VAD analyzer: `confidence` 0.7,
`start_secs` 0.2, `stop_secs` 0.2, `min_volume` 0.6. Published STT p99 latency figures
are measured at `stop_secs=0.2`. If you change `stop_secs`, re-run the stt-benchmark
with your settings and pass the measured value to the STT service as
`ttfs_p99_latency`. Prefer removing noise with an input audio filter over raising
`confidence` or `min_volume`.
Source: https://docs.pipecat.ai/pipecat/learn/speech-input

## Vapi

Pinned: unversioned rolling API, checked 11 September 2026 against the live OpenAPI
spec at https://api.vapi.ai/api-json.

`startSpeakingPlan.waitSeconds` is the floor on how long the agent waits before
replying. Default 0.4, min 0, max 5. The spec says this is the minimum it will wait,
and that pipeline latency will push past it. That sentence matters: `waitSeconds` is
the only latency knob the API gives you directly, and it cannot make the rest faster.
Source: https://docs.vapi.ai/customization/speech-configuration

Endpointing precedence, highest first: `customEndpointingRules`,
`smartEndpointingPlan`, `transcriptionEndpointingPlan`, then the transcriber's
built-in endpointing. Setting a lower-precedence plan while a higher one is present
changes nothing, which reads as a latency problem and is a config problem.
Source: https://docs.vapi.ai/customization/speech-configuration

`transcriptionEndpointingPlan` defaults: `onPunctuationSeconds` 0.1 (min 0, max 3),
`onNoPunctuationSeconds` 1.5 (min 0, max 3), `onNumberSeconds` 0.5 per the machine
default. The live spec contradicts itself on that last field: the prose says 0.4 and
the annotation says 0.5. Treat 0.5 as the machine-readable value and verify
empirically.
Source: https://api.vapi.ai/api-json

`smartEndpointingPlan` accepts a LiveKit provider with a `waitFunction` string,
default `200 + 8000 * x`. It maps probability x, where 0 is high confidence the caller
stopped, to milliseconds: 200 ms at x equal to 0 and 8200 ms at x equal to 1. Lower
the constant to cut the floor; lower the coefficient to cut the tail. LiveKit
endpointing is documented as English only.
Source: https://docs.vapi.ai/customization/speech-configuration

`server.timeoutSeconds` defaults to 20 for tool calls. That is 20 seconds of dead air
against a 5 s tool budget, so set it down explicitly on every tool.
Source: https://api.vapi.ai/api-json

A per-stage latency breakdown API (transcription, time to first token, time to first
byte, as separate fields) is not in the verified fact set:
verify against current docs.

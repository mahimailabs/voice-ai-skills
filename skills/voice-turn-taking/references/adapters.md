# Turn Taking Adapters

How the vendor-neutral knobs in SKILL.md map onto LiveKit Agents, Pipecat, and Vapi,
with a doc URL per claim and the version each claim was checked against.

## LiveKit Agents

Pinned to LiveKit Agents for Python 1.8.x, verified 11 September 2026.

### Mapping

| this skill | LiveKit 1.8.x |
| --- | --- |
| end-of-turn detector | `turn_handling["turn_detection"]` |
| min endpointing delay | `turn_handling["endpointing"]["min_delay"]`, default 0.5 |
| max endpointing delay | `turn_handling["endpointing"]["max_delay"]`, default 3.0 |
| fixed or dynamic | `turn_handling["endpointing"]["mode"]`, `"fixed"` or `"dynamic"` |
| VAD | the `vad` kwarg on `AgentSession` |
| user turn limits | `turn_handling["user_turn_limit"]["max_words"]` and `["max_duration"]` |

### Claims

- `AgentSession.__init__` deprecates `min_endpointing_delay`, `max_endpointing_delay`
  and `turn_detection` in favor of one `turn_handling=TurnHandlingOptions(...)` kwarg.
  `TurnHandlingOptions` is a `TypedDict(total=False)`, so a plain dict also works.
  Its five keys are `turn_detection`, `endpointing`, `interruption`,
  `preemptive_generation`, `user_turn_limit`.
  Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/turn.py
- TRAP: if you pass `turn_handling` and a legacy kwarg together, the legacy kwarg is
  discarded with no error. Never mix the two styles.
  Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/turn.py
- `EndpointingOptions` keys and defaults: `mode` `"fixed"`, `min_delay` 0.5,
  `max_delay` 3.0, `alpha` 0.9 (dynamic mode only). With a streaming turn detector,
  unset keys fall back to `min_delay` 0.3 and `max_delay` 2.5. These are the headline numbers
  in SKILL.md.
  Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/turn.py
- `turn_detection` accepts the strings `"stt"`, `"vad"`, `"realtime_llm"`, `"manual"`,
  or a detector instance. If absent, the session auto-selects in the order
  `realtime_llm`, `vad`, `stt`, `manual`. The auto-selected value can be VAD, which is
  the failure this skill is about. Set it explicitly.
  Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/agent_session.py
- The current turn detector is `inference.TurnDetector()`, built into livekit-agents
  with no separate plugin package. Keyword-only kwargs include `version`
  (`"v1"` or `"v1-mini"`), `unlikely_threshold`, `backchannel_threshold` and
  `local_fallback` (default `True`). Model strings are `turn-detector-v1` and
  `turn-detector-v1-mini`.
  Source: https://docs.livekit.io/agents/build/turns/turn-detector/
- The older text detector `livekit.plugins.turn_detector.multilingual.MultilingualModel`
  is labelled deprecated. Do not use it in a new 1.8.x agent.
  Source: https://docs.livekit.io/agents/build/turns/turn-detector/
- `vad` is not required. It defaults to the bundled `inference.VAD(model="silero")`.
  Pass `vad=None` to opt out, which this skill advises against on a phone line.
  VAD kwargs include `min_speech_duration` 0.05, `min_silence_duration` 0.25,
  `prefix_padding_duration` 0.5, `activation_threshold` 0.5.
  Source: https://docs.livekit.io/agents/build/turns/vad/
- `UserTurnLimitOptions` keys are `max_words` (default `None`) and `max_duration`
  (default `None`). Both off. Enabling either fires `UserTurnExceededEvent`.
  Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/turn.py
- CONFLICT: the turns docs page shows `min_delay` 0.6 and
  `max_delay` 1.2. Those values are not the defaults in the 1.8.1 source. Trust the
  source values (0.5 and 3.0, or 0.3 and 2.5 with a streaming detector) and treat any
  number on a docs page as illustrative.
  Source: https://docs.livekit.io/agents/build/turns/

### Snippets

Audio turn detector with the clinic settings.

```python
from livekit.agents import AgentSession, TurnHandlingOptions, inference

session = AgentSession(
    turn_handling=TurnHandlingOptions(
        turn_detection=inference.TurnDetector(),
        endpointing={"mode": "dynamic", "min_delay": 0.3, "max_delay": 2.5},
    ),
)
```

User turn limits, off unless the flow is scripted or the caller is adversarial.

```python
session = AgentSession(
    turn_handling={"user_turn_limit": {"max_words": 100, "max_duration": 30.0}},
)
```

Source for both forms: https://docs.livekit.io/agents/build/turns/

## Pipecat

Pipecat 1.0. Unversioned docs, checked 11 September 2026.

### Mapping

| this skill | Pipecat 1.0 |
| --- | --- |
| end-of-turn detector | a stop strategy in `UserTurnStrategies(stop=[...])` |
| min endpointing delay | `VADParams(stop_secs=...)` plus the analyzer's own decision |
| max endpointing delay | `SmartTurnParams(stop_secs=...)`, default 3.0 |
| VAD | `SileroVADAnalyzer(params=VADParams(...))` on the user aggregator |
| user turn limits | verify against current docs |

There is no single min and max endpointing pair. The floor comes from the VAD and the
ceiling comes from the analyzer's own `stop_secs`, which is a different field with the
same name. Read both before changing either.

### Claims

- The VAD analyzer is not on `TransportParams` in 1.0. It goes on
  `LLMUserAggregatorParams(vad_analyzer=...)` inside `LLMContextAggregatorPair`,
  because its speech start and stop signals feed the user turn strategies.
  Source: https://docs.pipecat.ai/pipecat/learn/speech-input
- `VADParams` fields and defaults: `confidence` 0.7, `start_secs` 0.2, `stop_secs` 0.2,
  `min_volume` 0.6. `SileroVADAnalyzer` takes `sample_rate` (8000 or 16000) and
  `params`. It ships as a core dependency, no extra install.
  Source: https://docs.pipecat.ai/api-reference/server/services/vad/silero-vad-analyzer
- The audio turn model is `LocalSmartTurnAnalyzerV3`, imported from
  `pipecat.audio.turn.smart_turn.local_smart_turn_v3`. It runs locally via ONNX with
  bundled weights and sub-100 ms CPU inference.
  Source: https://docs.pipecat.ai/api-reference/server/utilities/turn-detection/smart-turn-overview
- It attaches to the stop strategy, not to the transport or the worker:
  `TurnAnalyzerUserTurnStopStrategy(turn_analyzer=...)` inside
  `UserTurnStrategies(stop=[...])`, passed as
  `LLMUserAggregatorParams(user_turn_strategies=..., vad_analyzer=...)`.
  Source: https://docs.pipecat.ai/api-reference/server/utilities/turn-detection/smart-turn-overview
- As of v0.0.102 that pairing is the default stop strategy, with
  `SileroVADAnalyzer` at `stop_secs=0.2`. A new agent gets an audio turn detector
  without configuring anything.
  Source: https://docs.pipecat.ai/api-reference/server/utilities/turn-detection/smart-turn-overview
- `SmartTurnParams` defaults: `stop_secs` 3.0 (silence-based fallback end of turn,
  explicitly different from the VAD's `stop_secs`), `pre_speech_ms` 500.0,
  `max_duration_secs` 8.0. A turn classified incomplete is auto-completed once
  silence passes `stop_secs`. That is the max endpointing delay in this stack.
  Source: https://docs.pipecat.ai/api-reference/server/utilities/turn-detection/smart-turn-overview
- Other stop strategies from `pipecat.turns.user_stop`:
  `SpeechTimeoutUserTurnStopStrategy(user_speech_timeout=0.6, wait_for_transcript=True)`,
  `ExternalUserTurnStopStrategy(timeout=0.5, wait_for_transcript=True)`,
  `LLMTurnCompletionUserTurnStopStrategy(config=...)`.
  Source: https://docs.pipecat.ai/server/utilities/turn-management/user-turn-strategies
- Start strategies from `pipecat.turns.user_start` decide when a turn begins:
  `VADUserTurnStartStrategy`, `TranscriptionUserTurnStartStrategy(use_interim=True)`,
  `MinWordsUserTurnStartStrategy(min_words=..., use_interim=True)`,
  `WakePhraseUserTurnStartStrategy(phrases=...)`.
  Source: https://docs.pipecat.ai/server/utilities/turn-management/user-turn-strategies
- Tuning caveat: published STT P99 latency figures assume `stop_secs=0.2`. If you
  change it, re-run the stt-benchmark with your settings and pass the measured value
  to the STT service as `ttfs_p99_latency`. Prefer an upstream noise filter over
  raising `confidence` or `min_volume` on a noisy line.
  Source: https://docs.pipecat.ai/pipecat/learn/speech-input
- A hosted or remote smart-turn analyzer class name: verify against current docs.
  Only `LocalSmartTurnAnalyzerV3` appears on the smart-turn overview page.
  Source: https://docs.pipecat.ai/api-reference/server/utilities/turn-detection/smart-turn-overview
- User turn limits equivalent to max words and max duration: verify against current docs.

### Snippet

```python
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies

user_params = LLMUserAggregatorParams(
    user_turn_strategies=UserTurnStrategies(
        stop=[TurnAnalyzerUserTurnStopStrategy(
            turn_analyzer=LocalSmartTurnAnalyzerV3())]),
    vad_analyzer=SileroVADAnalyzer(),
)
```

Source: https://docs.pipecat.ai/api-reference/server/utilities/turn-detection/smart-turn-overview

## Vapi

Unversioned rolling API. Facts taken from the live OpenAPI spec and the speech
configuration page, checked 11 September 2026.

### Mapping

| this skill | Vapi |
| --- | --- |
| end-of-turn detector | `startSpeakingPlan.smartEndpointingPlan` |
| min endpointing delay | `startSpeakingPlan.waitSeconds`, default 0.4 |
| max endpointing delay | `transcriptionEndpointingPlan.onNoPunctuationSeconds`, default 1.5 |
| digit-case override | `startSpeakingPlan.customEndpointingRules` |
| VAD | not exposed as a separate knob. Verify against current docs |
| user turn limits | verify against current docs |

### Claims

- Endpointing precedence, highest first: `customEndpointingRules`,
  `smartEndpointingPlan`, `transcriptionEndpointingPlan`, then the transcriber's
  built-in endpointing. A smart plan overrides the transcription plan and is itself
  overridden by any matching custom rule.
  Source: https://api.vapi.ai/api-json
- `startSpeakingPlan.waitSeconds` default 0.4, min 0, max 5. Spec text: it is the
  minimum wait, and pipeline latency pushes the real number above it. Treat it as a
  floor, not as an end-to-end budget.
  Source: https://api.vapi.ai/api-json
- `transcriptionEndpointingPlan` defaults: `onPunctuationSeconds` 0.1,
  `onNoPunctuationSeconds` 1.5, `onNumberSeconds` 0.5 per the machine-readable
  default. The prose on the same field says 0.4. The spec contradicts itself here:
  verify against current docs before relying on either value.
  Source: https://api.vapi.ai/api-json
- `customEndpointingRules` is an array, default empty. Rule schemas:
  `AssistantCustomEndpointingRule`, `CustomerCustomEndpointingRule`,
  `BothCustomEndpointingRule`. Each carries `type`, `regex`, `regexOptions` and
  `timeoutSeconds` (min 0, max 15). The documented use case is exactly the digit case:
  a longer timeout while the caller enumerates numbers.
  Source: https://api.vapi.ai/api-json
- `smartEndpointingPlan` options: `VapiSmartEndpointingPlan`,
  `LivekitSmartEndpointingPlan` (`waitFunction` default `"200 + 8000 * x"`, mapping
  probability x to 200 ms at x=0 and 8200 ms at x=1), and
  `CustomEndpointingModelSmartEndpointingPlan`. Docs recommend the LiveKit plan for
  English only and the Vapi plan for other languages. Krisp (audio-based, threshold
  default 0.5), Deepgram Flux, and AssemblyAI end-of-turn are also available.
  Source: https://docs.vapi.ai/customization/speech-configuration
- `startSpeakingPlan.smartEndpointingEnabled` carries an empty description in the spec
  while `smartEndpointingPlan` is fully documented. Whether it is formally deprecated:
  verify against current docs.
  Source: https://api.vapi.ai/api-json

### Snippet

Clinic settings: a smart endpointing plan, plus a custom rule for the digit case.

```json
{
  "startSpeakingPlan": {
    "waitSeconds": 0.4,
    "smartEndpointingPlan": { "provider": "livekit", "waitFunction": "200 + 8000 * x" },
    "customEndpointingRules": [
      { "type": "customer", "regex": "[0-9]", "timeoutSeconds": 3 }
    ]
  }
}
```

Source: https://docs.vapi.ai/customization/speech-configuration

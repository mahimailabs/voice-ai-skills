# Pipeline shape adapters

How the four shapes map onto LiveKit Agents, Pipecat, and Vapi, with a doc URL per
claim. Pinned: LiveKit Agents 1.8.x, verified 11 September 2026 (facts read from the
1.8.1 wheel and docs on 11 September 2026). Pipecat 1.0 docs and Vapi unversioned
docs, checked 11 September 2026. Re-verify every identifier before you ship it.

## LiveKit Agents 1.8.x

One object, `AgentSession`, carries all four shapes. The shape is decided by which
parameters you fill.

### Cascade

Pass `stt`, `llm` and `tts`. The 1.8.x quickstart uses no per-vendor plugin packages:
model strings are `provider/model` through the inference gateway.
Source: https://docs.livekit.io/agents/start/voice-ai/

```python
from livekit.agents import AgentSession, inference

session = AgentSession(
    stt=inference.STT(model="deepgram/nova-3", language="multi"),
    llm=inference.LLM(model="google/gemma-4-31b-it"),
    tts=inference.TTS(model="inworld/inworld-tts-2", voice="Ashley"),
)
```

`vad` is not required. It defaults to the bundled Silero VAD
(`inference.VAD(model="silero")`); pass `vad=None` to opt out.
Source: the livekit-agents 1.8.1 wheel, `livekit/agents/voice/agent_session.py`
(https://pypi.org/project/livekit-agents/1.8.1/)

### Speech-to-speech

Pass a realtime model as `llm` and leave `stt` and `tts` unset. The parameter is typed
`llm.LLM | llm.RealtimeModel | llm.DuplexModel | LLMModels | str`, so the same keyword
takes a cascade LLM, a realtime model, or a full-duplex model.
Source: the livekit-agents 1.8.1 wheel, `AgentSession.__init__` at line 380
(https://pypi.org/project/livekit-agents/1.8.1/)

Turn detection auto-selects in the order `realtime_llm`, `vad`, `stt`, `manual` when
`turn_handling["turn_detection"]` is absent. A realtime model therefore takes the turn
decision away from your detector by default.
Source: the livekit-agents 1.8.1 wheel, `livekit/agents/voice/turn.py`

### Half-cascade

The exact realtime-model class and the keyword for a text-only response modality:
verify against current docs. The one stated constraint is negative, below.

### Full-duplex

```python
from livekit.agents import AgentSession, inference
from livekit.plugins.openai.realtime import GPTLiveModel

session = AgentSession(
    llm=GPTLiveModel(voice="marin"),
    vad=inference.VAD(model="silero"),  # required: the session drops its default here
)
```

Facts that decide the shape, all from
https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/ :

- No half-cascade. GPT-Live has no text-only response modality, so it cannot be paired
  with a TTS plugin in a half-cascade setup.
- `session.say()` raises unless a TTS is attached, and even then the model can speak
  over the TTS and never hears it. For exact wording, the docs send you to a cascade.
- Barge-in needs a VAD passed explicitly. The session drops its default VAD for this
  model, and without one the agent plays until the model stops on its own.
- The voice model never sees your tools. Work is delegated to a backend model
  (`delegation="responses"` by default), which decides which tools to call.
- `GPTLiveModel` has no `instructions` parameter. Instructions live on the `Agent`.
- Install: `uv add "livekit-agents[openai]~=1.8"`. Requires an OpenAI API key on an
  account with GPT-Live alpha access.

Pricing: LiveKit's docs state no rate. OpenAI lists 0.05 USD per minute for the voice
model, billed per second, with the backend model and tools charged separately.
Re-check current pricing. Source: https://developers.openai.com/api/docs/pricing

## Pipecat 1.0

The shape is the ordered list you hand to `Pipeline`.

### Cascade

Canonical order: `transport.input(), stt, aggregators.user(), llm, tts,
transport.output(), aggregators.assistant()`. Ordering is load-bearing: the assistant
aggregator must come after `transport.output()` so that only text actually spoken
reaches the context. Source: https://docs.pipecat.ai/pipecat/learn/your-first-agent

The runnable object in 1.0 is `PipelineWorker`
(`from pipecat.pipeline.worker import PipelineParams, PipelineWorker`), driven by
`WorkerRunner`. `PipelineTask` and `PipelineRunner` are deprecated aliases.
Source: https://docs.pipecat.ai/pipecat/learn/your-first-agent

The system prompt is set with `system_instruction` in the LLM service's `Settings`,
not as a context message.
Source: https://docs.pipecat.ai/pipecat/learn/function-calling

The VAD analyzer is not on `TransportParams` in 1.0. It is passed as
`LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer())` into
`LLMContextAggregatorPair`. Source: https://docs.pipecat.ai/pipecat/learn/speech-input

### Speech-to-speech, half-cascade, full-duplex

Service class names and constructor keywords: verify against current docs. The fact
pack behind this file covers only the cascade path for Pipecat, so no identifier is
asserted here.

## Vapi

The shape is decided by which assistant blocks you fill. Vapi's API is unversioned and
rolling, checked 11 September 2026 against https://api.vapi.ai/api-json .

### Cascade

Set `transcriber`, `model` and `voice` as three separate blocks, each discriminated on
`provider`. The system prompt goes in `model.messages` as an object with
`role: "system"`. Source: https://docs.vapi.ai/openai-realtime

### Speech-to-speech

Keep a single `model` block with `provider: "openai"` and a realtime model id.
Production id: `gpt-realtime-2025-08-28`. Preview ids:
`gpt-4o-realtime-preview-2024-12-17` and `gpt-4o-mini-realtime-preview-2024-12-17`.
Vapi's docs contrast this with "other Vapi configurations which orchestrate a
transcriber, model and voice API to simulate speech-to-speech".
Source: https://docs.vapi.ai/openai-realtime

The block keeps the same shape as a cascade model block: `provider`, `model`, and a
`messages` array carrying the system prompt. The `transcriber` block falls away. The
`voice` block does not: it narrows to the short list below.

Voice restriction, and the reason brand control costs you here: realtime models accept
only `alloy`, `echo`, `shimmer` (standard) plus `marin` and `cedar` (realtime only).
`ash`, `ballad`, `coral`, `fable`, `onyx` and `nova` are not supported.
Source: https://docs.vapi.ai/openai-realtime

### Half-cascade and full-duplex

Whether Vapi exposes a text-only realtime response modality, or any non-OpenAI
speech-to-speech model: verify against current docs.

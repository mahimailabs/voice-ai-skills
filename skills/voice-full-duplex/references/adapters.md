# Full-Duplex Adapters

The vendor mapping for every rule in SKILL.md, with a doc URL per claim and the pinned
version. Only one stack ships a full-duplex model today. Verify before you ship.

Pinned: LiveKit Agents 1.8.x (source read at 1.8.1), verified 11 September 2026.
Pipecat 1.0 docs and Vapi unversioned docs, checked 11 September 2026.

## Knob mapping

| neutral knob | LiveKit Agents 1.8.x | Pipecat 1.0 | Vapi |
| --- | --- | --- | --- |
| full-duplex model | `GPTLiveModel`, passed as `llm` | verify against current docs | verify against current docs |
| turn detector effect | none, the model owns turns | verify against current docs | not applicable, turn-based |
| VAD required | yes, pass it explicitly | verify against current docs | not applicable |
| persona location | `Agent(instructions=...)` | verify against current docs | `model.messages` with role system |
| tool delegation | `delegation="responses"` | verify against current docs | not applicable |
| verbatim speech | `session.say()` raises without a TTS | verify against current docs | not applicable |
| text-only mode | none, no half-cascade | verify against current docs | not applicable |
| startup context cap | 128 messages and 8192 tokens | verify against current docs | verify against current docs |
| post-start edits | append-only, edits logged and dropped | verify against current docs | verify against current docs |
| side channels | three, 500 tokens per append | verify against current docs | verify against current docs |
| reply refusal | `generate_reply` fails after 10 s | verify against current docs | verify against current docs |
| persona change | needs a new connection | verify against current docs | verify against current docs |

## LiveKit Agents

Import and constructor. `from livekit.plugins.openai.realtime import GPTLiveModel`.
The same module exports `GPTLiveDelegation`, `GPTLiveSession`, `GPTLiveVoices` and
`ResponsesDelegationOptions`. Install `uv add "livekit-agents[openai]~=1.8"`.
Parameters: `model` (default `gpt-live-1`), `voice` (default `marin`), `delegation`
(`responses` or `client`, default `responses`), `responses_options`, `api_key`,
`base_url`, `http_session`, `max_session_duration`, `conn_options`.
Voice and delegation are immutable once the session starts.
Source: https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/

```python
from livekit.agents import AgentSession, inference
from livekit.plugins.openai.realtime import GPTLiveModel
session = AgentSession(
    vad=inference.VAD(model="silero"),
    llm=GPTLiveModel(
        voice="marin",
        responses_options={"model": "gpt-5.6-luna",
                           "instructions": "Use tools when current information is required."},
    ),
)
```

No `instructions` parameter on the model. Set them on the `Agent`. Setting new
instructions mid-session raises `RealtimeError` and the original persona keeps running.
Source: https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/

Rule 1, no forced stop. "The model controls turn detection and barge-in. The LiveKit
turn detection options can't change that." Passing a turn detector is not documented as
an error, only as having no effect. Playback is cut by the session's own interruption
detection, "which needs a VAD. Pass one explicitly, because the session drops its
default VAD for this model." Without a VAD the agent plays until the model stops.
There is no message truncation. An interrupted turn stays whole in the model's context,
and the model can refer to something the caller never heard.
Source: https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/

Rule 2, tools. The voice model does not see the tools, so do not describe them in the
persona. With `delegation="responses"` the backend model decides which tools to call.
The framework runs your `@function_tool` methods in your process and returns each
result to it. With `delegation="client"` there is no tool channel: the
plugin ignores `@function_tool` methods and the source raises `RealtimeError` if any
are registered. `responses_options` accepts `model` (the only key with a plugin
default, `gpt-5.6-luna`), `instructions`, `tool_choice`, `parallel_tool_calls`,
`reasoning`, `text`, `service_tier` and `max_output_tokens`.
Source: https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/

Rule 3, say(). "GPT-Live can't speak a script word for word. session.say() raises an
error unless you attach a TTS to the AgentSession. Even then, the model can speak at
the same time as the TTS, and it never receives the TTS audio." There is no text-only
response modality, so no half-cascade is possible with this model.
Source: https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/

Rule 5, context. A `chat_ctx` passed before start becomes the startup history, capped
at 128 messages and 8192 rendered tokens, oldest dropped first. The source constant is
`_MAX_INPUT_ITEMS = 128`. After start the history is append-only: an edit or a delete
logs a warning and the model keeps the original. A handoff that changes instructions or
chat context opens a new connection and re-sends the conversation under the same caps;
a handoff that changes only tools keeps the connection.
Source: https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/

Three channels exist on the duplex session, 500 tokens per append. None of them reach
`session.history`. `append_instructions` carries developer guidance for the rest of the
session. `append_thinking` carries silent context, used only if it becomes relevant.
`append_commentary` is something to say now, in the model's own words.
The three calls are verbatim; the strings are the clinic's.
Source: https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/

```python
self.duplex_session.append_thinking("This caller has missed two appointments.")
self.duplex_session.append_commentary(
    "Tell the caller the three fifteen slot just opened up.")
self.duplex_session.append_instructions("Confirm the date of birth before you book.")
```

Reply refusal. `generate_reply()` appends the instruction as commentary, not as a
direct utterance, and the model may refuse. The source constant is
`_REPLY_TIMEOUT = 10.0`: if the model has not started speaking ten seconds after the
request, the framework marks the handle done with a `RealtimeError`. A newer request, a
reconnect, or a closed session ends a pending reply the same way. Await the handle,
then call `handle.exception()` to find out whether the model answered.
Source: https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/

```python
handle = self.session.generate_reply(instructions="Greet the caller and ask how you can help.")
await handle
if handle.exception() is not None:
    logger.info("the model declined to greet the caller")
```

Turn segmentation and other controls. Turn boundaries are computed by the framework,
not marked by the model: each continuous stretch of output is one turn, and a pause
under about half a second does not split it. Transcripts arrive after the audio.
`mute_input()` replaces the microphone with silence and the model keeps generating.
As the session nears the context limit the service compacts history itself.
Source: https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/

Metrics and price. The voice model reports cumulative session seconds about once a
minute, emitted as the `session_duration` field of a `RealtimeModelMetrics` event; the
backend model's tokens arrive as `LLMMetrics` under its own name. Totals are on
`session.usage`. LiveKit's docs state no rate and point at the model vendor's pricing
page. That page lists 0.05 USD per minute, billed per second, with the backend model
and tools charged separately. Re-check current pricing.
Sources: https://docs.livekit.io/agents/models/realtime/plugins/gpt-live/ and
https://developers.openai.com/api/docs/pricing

## Pipecat

No full-duplex service class appears in the 1.0 pages checked on 11 September 2026.
The documented shape is a cascade: an ordered `Pipeline` list with a transport, an STT
service, a user aggregator, an LLM service, a TTS service and an assistant aggregator.
Turn control lives in user turn start and stop strategies on the user aggregator.
That is the opposite arrangement to a model that owns its own turns.
Full-duplex support, service class names, and context limits: verify against current docs.
Source: https://docs.pipecat.ai/pipecat/learn/your-first-agent

## Vapi

Vapi exposes a turn-based speech-to-speech model, not a full-duplex one. It is set as a
normal `model` block with `provider: "openai"` and a realtime model id. The production
id is `gpt-realtime-2025-08-28`; the preview ids are
`gpt-4o-realtime-preview-2024-12-17` and `gpt-4o-mini-realtime-preview-2024-12-17`.
Realtime models accept only `alloy`, `echo`, `shimmer`, `marin` and `cedar` as voices.
Source: https://docs.vapi.ai/openai-realtime

Turn control stays with `startSpeakingPlan` and `stopSpeakingPlan` on the assistant.
Those knobs are what a full-duplex model would take away, so their presence is the
signal that the model is turn-based. The system prompt stays in `model.messages` with
role `system`, and tools stay in the same model block.
Any full-duplex offering beyond this: verify against current docs.
Source: https://api.vapi.ai/api-json

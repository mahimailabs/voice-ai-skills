# Voice Prompting Adapters

Where the system prompt lives on each stack, with a doc URL per claim.

Pinned versions: LiveKit Agents 1.8.x, verified 11 September 2026. Pipecat 1.0 docs,
checked 11 September 2026. Vapi: unversioned docs, checked 11 September 2026.

## LiveKit Agents 1.8.x

- The system prompt is `instructions` on an `Agent` subclass. It is keyword-only and
  required, typed `str | Instructions`.
  Source: https://docs.livekit.io/agents/start/voice-ai/
- The quickstart prompt already carries a spoken-output rule verbatim: responses are
  "without any complex formatting or punctuation including emojis, asterisks, or other
  symbols". Replace that sentence with the full spoken-output block.
  Source: https://docs.livekit.io/agents/start/voice-ai/
- One reply can override the prompt: `session.generate_reply(instructions=...)`. Every
  argument on that method is keyword-only.
  Source: https://docs.livekit.io/agents/start/voice-ai/
- `AgentSession` also accepts `tts_text_transforms` and `use_tts_aligned_transcript`.
  Their accepted values and defaults: verify against current docs.
  Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/agent_session.py

Assemble the four blocks as separate Python strings, then concatenate once.

```python
from livekit.agents import Agent

class ClinicAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SPOKEN + PERSONA + TASK + CONFIRM)
```

Source: https://docs.livekit.io/agents/start/voice-ai/

## Pipecat 1.0

- The system prompt is `system_instruction` inside the LLM service `Settings`, not a
  context message. The docs state it verbatim: the personality "is set via
  `system_instruction` in the LLM service's Settings, not as a context message".
  Source: https://docs.pipecat.ai/pipecat/learn/function-calling
- The `Settings` object is nested on the service class, for example
  `OpenAILLMService(api_key=..., settings=OpenAILLMService.Settings(system_instruction="..."))`.
  Source: https://docs.pipecat.ai/pipecat/learn/your-first-agent
- The context object is `LLMContext`, and aggregators come from
  `LLMContextAggregatorPair(context)`. Keep the prompt out of both.
  Source: https://docs.pipecat.ai/pipecat/migration/migration-1.0

```python
from pipecat.services.openai.llm import OpenAILLMService

settings = OpenAILLMService.Settings(system_instruction=SPOKEN + PERSONA + TASK + CONFIRM)
llm = OpenAILLMService(api_key=key, settings=settings)
```

Source: https://docs.pipecat.ai/pipecat/learn/your-first-agent

## Vapi

- The system prompt is one entry in `model.messages` with `role` set to `system` and
  the prompt in `content`. The role enum is
  `['assistant','function','user','system','tool']`.
  Source: https://docs.vapi.ai/openai-realtime
- The greeting is not part of the prompt. It is the top-level `firstMessage` field,
  alongside `firstMessageMode` and `firstMessageInterruptionsEnabled`. The
  spoken-output rules apply to `firstMessage` too, and nothing enforces them there.
  Source: https://api.vapi.ai/api-json
- The model block also carries `temperature` and `maxTokens`. A low `maxTokens` is not
  a substitute for a word count in the prompt: it truncates mid-sentence.
  Source: https://api.vapi.ai/api-json

```python
model = {
    "provider": "openai",
    "model": MODEL,
    "messages": [{"role": "system", "content": SPOKEN + PERSONA + TASK + CONFIRM}],
}
assistant = {"model": model, "firstMessage": GREETING}
```

Source: https://docs.vapi.ai/openai-realtime

## Not verified on any stack

Number and date normalization is a property of the TTS provider, not of these three
frameworks. None of the fact sources states a framework-level number formatter. Treat
the prompt as the only control you have here. Before relying on provider-side
normalization or a pronunciation dictionary, verify against current docs.

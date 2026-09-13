# The clinic agent

One agent, two stacks. The same appointment booking agent for Riverside Family
Medicine appears in all ten skills, so the rules compose instead of contradicting.

It answers the clinic's main line, identifies the caller by name and date of birth,
offers up to three appointment times, reads the booking back, books it, and says a
confirmation number. It gives no clinical advice.

## Run

LiveKit Agents 1.8:

```
uv run --with "livekit-agents~=1.8" --with python-dotenv livekit_agent.py dev
```

Pipecat 1.10:

```
uv run --with "pipecat-ai[daily,deepgram,cartesia,openai,silero]~=1.10" --with python-dotenv pipecat_agent.py
```

Both need a `.env` next to the file. LiveKit reads `LIVEKIT_URL`, `LIVEKIT_API_KEY` and
`LIVEKIT_API_SECRET`; the speech and language stages bill through that account. Pipecat
reads `DAILY_ROOM_URL`, `DAILY_TOKEN`, `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY`,
`CARTESIA_VOICE_ID` and `OPENAI_API_KEY`.

The files are named `livekit_agent.py` and `pipecat_agent.py` on purpose. A file named
`livekit.py` or `pipecat.py` shadows the SDK package of the same name and the import
fails.

Both files carry stand-in scheduling functions at the bottom (`_find_patient`,
`_availability`, `_book`). Replace them with a real client.

## Which line demonstrates which skill

| Line | What it shows | Skill |
| --- | --- | --- |
| `stt=`, `llm=`, `tts=` and the `Pipeline([...])` order | A cascade, chosen because dates and confirmation numbers must be exact. | [voice-pipeline-choice](../../skills/voice-pipeline-choice/) |
| `turn_detection`, `endpointing`, `TurnAnalyzerUserTurnStopStrategy` | An audio turn model in front of the endpointing window, so a caller reading digits is not cut off. | [voice-turn-taking](../../skills/voice-turn-taking/) |
| `interruption={"min_words": 2, ...}`, `MinWordsUserTurnStartStrategy(min_words=2)` | A word floor, so backchannels on a phone line do not stop the agent. | [voice-interruptions](../../skills/voice-interruptions/) |
| `context.disallow_interruptions()`, `allow_interruptions=False`, `FunctionCallUserMuteStrategy` | The read-back gate. The confirmation cannot be cut off. | [voice-interruptions](../../skills/voice-interruptions/) |
| `conversation_item_added` handler, `MetricsLogObserver` | Five timings per turn, not one average. | [voice-latency-budget](../../skills/voice-latency-budget/) |
| `INSTRUCTIONS` | Spoken output, persona, task, and confirmation as four separate blocks. | [voice-prompting](../../skills/voice-prompting/) |
| `TOOL_TIMEOUT`, `with_filler(...)`, `tool_options(timeout_secs=...)`, `max_tool_steps=3` | Every tool has a deadline and a sentence to say while it runs. | [voice-function-tools](../../skills/voice-function-tools/) |
| Tool docstrings and `Args:` blocks | Tool descriptions written for a spoken sentence, not for a reader. | [voice-function-tools](../../skills/voice-function-tools/) |
| `_DropPII`, and the `lookup_patient` log line | Both frameworks log tool arguments at DEBUG, and the dev command runs at DEBUG. The LiveKit file strips `lk.pii.*` keys on every handler. The Pipecat file logs no arguments of its own; run it at INFO or add a filter. | [voice-function-tools](../../skills/voice-function-tools/) |

## What the two files do differently

The read-back gate is the one place the stacks are not equivalent. One offers a
per-utterance flag that makes a single sentence uninterruptible. The other treats
"do not interrupt" and "ignore what the caller said" as separate settings, so speech
over the agent still becomes a turn unless you mute the input. Read
[voice-interruptions](../../skills/voice-interruptions/) before porting this part.

Neither file is production ready. There is no telephony, no eval suite, and no
persistence. Score it with [voice-agent-review](../../skills/voice-agent-review/) and
you will find those gaps, which is the point.

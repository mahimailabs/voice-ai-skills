# Interruption Adapters

The vendor mapping for every knob in SKILL.md, with a doc URL per claim and the
pinned version. Verify each call against current docs before you ship it.

## Knob mapping

| neutral knob | LiveKit Agents 1.8.x | Pipecat 1.0 | Vapi |
| --- | --- | --- | --- |
| interruptions enabled | `turn_handling["interruption"]["enabled"]`, default True | `enable_interruptions` on a user turn start strategy, default True | no session-level switch found, verify against current docs |
| min interruption duration | `min_duration`, default 0.5 | verify against current docs | `stopSpeakingPlan.voiceSeconds`, default 0.2, used only when `numWords` is 0 |
| min interruption words | `min_words`, default 0 | `MinWordsUserTurnStartStrategy(min_words=...)` | `stopSpeakingPlan.numWords`, default 0, max 10 |
| false interruption timeout | `false_interruption_timeout`, default 2.0 | verify against current docs | verify against current docs |
| resume after false interruption | `resume_false_interruption`, default True | verify against current docs | verify against current docs |
| audio during an uninterruptible segment | `discard_audio_if_uninterruptible`, default True | mute strategies discard it, disabled interruptions do not | verify against current docs |
| per-utterance gate | `allow_interruptions=False` on `say` or `generate_reply` | `user_mute_strategies` on the user aggregator | verify against current docs |
| backchannel phrase list | `backchannel_boundary`, default `(1.0, 1.0)`, semantics not documented | verify against current docs | `stopSpeakingPlan.acknowledgementPhrases`, ships with a default list |
| always-interrupt phrase list | verify against current docs | verify against current docs | `stopSpeakingPlan.interruptionPhrases`, ships with a default list |
| back off after a stop | verify against current docs | verify against current docs | `stopSpeakingPlan.backoffSeconds`, default 1, max 10 |

## LiveKit Agents

Pinned 1.8.x (source read at 1.8.1), verified 11 September 2026.

All interruption knobs moved into one kwarg. `min_interruption_duration`,
`min_interruption_words`, `allow_interruptions`, `false_interruption_timeout`,
`resume_false_interruption` and `discard_audio_if_uninterruptible` are deprecated on
`AgentSession.__init__` and replaced by `turn_handling=TurnHandlingOptions(...)`.
Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/turn.py

Trap: if you pass `turn_handling` and a legacy kwarg together, the legacy kwarg is
discarded with no error and no warning. Never mix the two styles.
Source: same wheel, `livekit/agents/voice/agent_session.py`.

`InterruptionOptions` is a `TypedDict`, so a plain dict works. Keys and defaults:
`enabled` True, `mode` (`"adaptive"` or `"vad"`, no default, absent means auto),
`discard_audio_if_uninterruptible` True, `min_duration` 0.5, `min_words` 0,
`resume_false_interruption` True, `false_interruption_timeout` 2.0,
`backchannel_boundary` `(1.0, 1.0)`.
Source: same wheel, `livekit/agents/voice/turn.py`.

```python
from livekit.agents import AgentSession

session = AgentSession(
    turn_handling={
        "interruption": {"min_duration": 0.5, "min_words": 2},
    },
)
```

One gated utterance. `allow_interruptions` is live on both `say` and
`generate_reply`, and only the constructor-level kwarg is deprecated.
Source: https://docs.livekit.io/agents/build/audio/

```python
handle = session.say(
    "Tuesday the fourteenth at three fifteen with Doctor Osei.",
    allow_interruptions=False,
)
await handle.wait_for_playout()
```

Inside a function tool, call `context.disallow_interruptions()` on the `RunContext`.
It takes no arguments, and it raises `RuntimeError` if the handle is already
interrupted. It also releases an active false-interruption pause.
Source: https://docs.livekit.io/agents/logic/tools/definition/

```python
@function_tool()
async def book_appointment(self, context: RunContext, slot_id: str) -> str:
    """Book the confirmed slot."""
    context.disallow_interruptions()
```

`session.interrupt(force=False)` stops current speech. Speech queued with
`allow_interruptions=False` keeps playing, along with everything behind it, unless
`force=True`. Setting `SpeechHandle.allow_interruptions` to False after the handle is
already interrupted raises `RuntimeError`.
Source: same wheel, `livekit/agents/voice/agent_session.py`.

Note on the numbers: the interruptions doc page returned HTTP 404 at the time of
checking, so these defaults come from the 1.8.1 source, not from prose. One doc
summary reported `min_duration` as 0.1. That value is not in the source. Trust 0.5 and
verify against current docs.

## Pipecat

1.0, unversioned docs, checked 11 September 2026.

The most important fact for the read-back gate: disabling interruptions does not
ignore the caller. The docs state that speech over the bot is still transcribed and
processed as a normal user turn. The reply is queued and plays when the current speech
finishes. To finish speaking and discard what the caller said over it, use mute
strategies instead.
Source: https://docs.pipecat.ai/pipecat/fundamentals/interruptions

`PipelineParams(allow_interruptions=..., interruption_strategies=[...])` is the old
0.0.x API and removed parameters are silently ignored. The replacement is
`enable_interruptions` on a user turn start strategy.
`MinWordsInterruptionStrategy` no longer exists either.
Source: https://docs.pipecat.ai/pipecat/migration/migration-1.0

```python
from pipecat.turns.user_start import (
    MinWordsUserTurnStartStrategy,
    VADUserTurnStartStrategy,
)

start_strategy = MinWordsUserTurnStartStrategy(min_words=2)
# Or disable barge-in entirely, which still queues the caller's turn:
start_strategy = VADUserTurnStartStrategy(enable_interruptions=False)
```

The `min_words` threshold applies only while the bot is speaking, so brief
affirmations do not interrupt. That is the word floor under a different name.
Source: https://docs.pipecat.ai/pipecat/fundamentals/interruptions

Mute strategies are the real gate. Pass them on `LLMUserAggregatorParams`. Built in:
`FirstSpeechUserMuteStrategy` (the greeting only),
`MuteUntilFirstBotCompleteUserMuteStrategy`, `FunctionCallUserMuteStrategy` (during
function calls) and `AlwaysUserMuteStrategy`. Multiple strategies combine with OR. The
docs warn against using the first two together.
Source: https://docs.pipecat.ai/pipecat/fundamentals/interruptions

```python
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.turns.user_mute import AlwaysUserMuteStrategy

user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
    context,
    user_params=LLMUserAggregatorParams(
        user_mute_strategies=[AlwaysUserMuteStrategy()],
    ),
)
```

After an interruption only the words actually spoken reach the context, because text
frames are pushed in sync with audio playback. Observe it with the
`on_assistant_turn_stopped` handler on the assistant aggregator, which carries
`message.interrupted` and `message.content`. Use that to log read-back completion.
Source: https://docs.pipecat.ai/pipecat/fundamentals/interruptions

To stop the bot from your own code, call `await self.broadcast_interruption()` inside
a `FrameProcessor`, or queue an `InterruptionWorkerFrame` on the worker.
Source: https://docs.pipecat.ai/pipecat/fundamentals/interruptions

A false-interruption resume equivalent is not documented. Verify against current docs.

## Vapi

Unversioned docs, checked 11 September 2026. Facts from the live OpenAPI spec.

`stopSpeakingPlan` holds the barge-in floors. Two more fields hold the phrase lists.
Source: https://api.vapi.ai/api-json

| field | default | bounds | note |
| --- | --- | --- | --- |
| `numWords` | 0 | 0 to 10 | the word floor |
| `voiceSeconds` | 0.2 | 0 to 0.5 | the duration floor, used only when `numWords` is 0 |
| `backoffSeconds` | 1 | 0 to 10 | wait after a stop before speaking again |
| `acknowledgementPhrases` | see below | | these never interrupt |
| `interruptionPhrases` | see below | | these always interrupt, whatever `numWords` says |

```python
stop_speaking_plan = {
    "numWords": 2,
    "backoffSeconds": 1,
    "acknowledgementPhrases": ["mm-hmm", "okay", "yeah", "right", "uh-huh", "sure"],
    "interruptionPhrases": ["stop", "wait", "hold", "actually", "no"],
}
```

The shipped defaults already cover the backchannel list in references/defaults.md.
Source: https://api.vapi.ai/api-json

Default `acknowledgementPhrases`: 'i understand', 'i see', 'i got it', 'i hear you',
'im listening', 'im with you', 'right', 'okay', 'ok', 'sure', 'alright', 'got it',
'understood', 'yeah', 'yes', 'uh-huh', 'mm-hmm', 'gotcha', 'mhmm', 'ah', 'yeah okay',
'yeah sure'.

Default `interruptionPhrases`: 'stop', 'shut', 'up', 'enough', 'quiet', 'silence',
'but', 'dont', 'not', 'no', 'hold', 'wait', 'cut', 'pause', 'nope', 'nah',
'nevermind', 'never', 'bad', 'actually'.

Note that 'no' and 'not' sit in the always-interrupt list, and that list overrides
`numWords`. This stack therefore cannot hold the read-back gate whole. It holds
against a stray "yes" and against backchannels, which is the failure the gate exists
to prevent, and it does not hold against an explicit rejection. Decide which you want.
To hold the gate completely, strip the rejection words from `interruptionPhrases` for
the read-back turn and put them back afterwards. To keep the shipped list, accept that
a caller saying "no, not Tuesday" cuts the read-back, and make sure the turn that
follows re-reads the whole booking rather than resuming mid sentence.

`firstMessageInterruptionsEnabled` is a top-level assistant field and gates the
greeting. Set it to allow interruptions there, since repeat callers open with intent.
Source: https://api.vapi.ai/api-json

A per-utterance uninterruptible flag for a single read-back sentence, and a
false-interruption resume timeout, are not in the spec fields read here. Verify
against current docs before you claim either exists.

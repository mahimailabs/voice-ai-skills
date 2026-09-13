---
name: voice-turn-taking
description: Decide when the caller has finished speaking. Covers VAD, endpointing min and max delay, semantic and audio end-of-turn models, transcription-based turn signals, and user turn limits. Use when the agent keeps interrupting callers or talks over them, waits too long before replying, cuts people off mid-sentence, interrupts someone reading a phone number or date of birth digit by digit, or when tuning turn detection, endpointing, VAD thresholds, or silence timeouts.
license: MIT
metadata:
  author: mahimairaja
  version: "0.1.0"
  category: voice-ai
---

# Voice Turn Taking

This skill decides when the caller has stopped speaking and the agent may reply.
It picks the end-of-turn detector and sets the two endpointing delays.

## Use this when

- The agent replies before the caller has finished a sentence.
- The agent cuts in between digit groups of a phone number or a date of birth.
- There is a second or more of dead air after the caller clearly stopped.
- The agent waits for a second caller utterance before answering the first.
- You are setting turn detection, endpointing delays, or VAD thresholds.

## Do not

- Do not use VAD alone to decide end of turn. It only knows that audio went quiet.
- Do not set min endpointing delay below 0.3 s. The turn commits before the transcript finalizes.
- Do not set max endpointing delay above 3.0 s without a written reason.
- Do not run a semantic detector with no VAD in front of it. It will fire on noise.
- Do not tune on your own voice only. You pause where your callers do not.
- Do not tune endpointing to fix latency that is really in the LLM or the TTS.
- Do not leave user turn limits on by default. They cut real callers mid-sentence.

## The four end-of-turn signals

Weakest to strongest. Each one knows something the one above it does not.

| signal | what it actually knows |
| --- | --- |
| VAD silence | audio energy dropped for N milliseconds. Nothing about words or meaning |
| transcription endpoint | the STT provider closed a segment. Knows words, not whether the thought ended |
| semantic text model | the transcript reads as a complete sentence. Waits on a transcript existing |
| audio turn model | pitch, pace, and trailing prosody say the caller handed the turn back |

Stack them. Let the strongest signal available make the decision, and let the weaker
ones gate it. An audio turn model still needs a VAD in front to know when to run.

## VAD is a gate, not a decision

**VAD tells you speech is happening. It never tells you speech is finished.**

A VAD min silence of 0.2 to 0.5 s exists to separate speech from line noise.
Reusing that value as end of turn cuts the caller off at the first breath.
Every stack ships a VAD default. None ships an end-of-turn policy for your callers.

## Headline defaults

| knob | default |
| --- | --- |
| min endpointing delay | 0.5 s, or 0.3 s with an audio turn detector |
| max endpointing delay | 3.0 s, or 2.5 s with an audio turn detector |
| VAD min silence | 0.2 to 0.5 s, a speech gate only |
| user turn limits (max words, max duration) | off |

Ranges, symptoms, and per-caller-type settings are in
[references/defaults.md](references/defaults.md).

## Symptom table

| symptom | likely cause | knob | direction |
| --- | --- | --- | --- |
| agent cuts off mid-sentence | min delay under the caller's natural pause | min endpointing delay | raise 0.2 s at a time, cap at 1.0 s |
| agent cuts off between digits | a 0.6 s gap between digit groups read as end of turn | detector first | add an audio turn detector and hold min at 0.3 s. Raise min to 0.8 s only if you cannot add one |
| long dead air after the caller stops | the detector never fires, max delay is doing the work | end-of-turn detector | fix the detector, then lower max toward 3.0 s |
| agent replies to half a sentence | VAD silence is deciding the turn | turn detection mode | move the decision off VAD |
| agent never replies until the caller speaks again | max delay above 3.0 s, or waiting on a final transcript | max endpointing delay | lower to 3.0 s |
| agent replies during a thinking pause | min delay below the caller's filler pause | min endpointing delay | raise to 0.6 to 0.8 s |
| agent talks over a slow speaker | fixed delays tuned on one fast talker | endpointing mode | switch to dynamic |
| noisy line starts turns on its own | VAD activation on background noise | VAD activation threshold and min speech duration | raise the threshold, and raise min speech duration so a 50 ms click cannot open a turn |
| short answers feel slow after fixing the digit case | one fixed min delay serving both cases | endpointing mode | switch to dynamic, hold min at 0.3 s |

## Procedure

1. Measure end-of-turn delay first: the gap from the caller's last word to the moment
   the turn is declared over, across 50 turns. It is usually the largest single share
   of the pause the caller feels, which runs from last word to first agent audio.
2. Pick the detector. Use the strongest one your stack ships, with a VAD in front.
   VAD alone is not an option on a phone line.
3. Set min, then max. Start at the headline default for your detector. Change one
   value per pass.
4. Run the five caller types below. Each exercises a different failure.
5. Watch the symptom table. Map each complaint to one knob and one direction.
6. Re-measure on a real phone call, not a laptop on Wi-Fi. Narrowband audio and
   jitter change how the detector behaves.

## The five caller types test

| caller type | what breaks | what to check |
| --- | --- | --- |
| fast talker | the agent feels a beat behind on every turn | min delay, dynamic mode, preemptive generation |
| list reader | the agent answers after item two of five | max delay, and a detector that sees an incomplete phrase |
| number reader | the agent cuts in between digit groups | audio turn detector first, min delay second |
| long pauser | the agent replies into a thinking pause | min delay at 0.8 s, max delay at 3.0 s |
| non-native speaker | mid-phrase pauses read as end of turn | a multilingual detector, min delay raised, then re-measure |

## The clinic case: a date of birth read digit by digit

The clinic agent identifies a caller by full name and date of birth before booking.
The caller reads theirs as "eleven, oh four, nineteen fifty two", 0.6 s between groups.

| min delay | what the agent does |
| --- | --- |
| 0.3 s | the gap after "eleven" ends the turn. The agent asks for the date again, twice. The caller repeats themselves and the call runs 40 seconds long |
| 0.8 s | the full date arrives intact. Every yes or no answer for the rest of the call now costs an extra 0.5 s, including the read-back |

The right answer is neither. Use an audio turn detector at min 0.3 s, max 2.5 s.
After "eleven" the pitch is still rising and the phrase is unfinished, so the
detector holds through the gap. After "nineteen fifty two" it falls and the detector
releases. Do not buy the digit case with a global 0.8 s min delay. You would pay it
on every turn of every call to fix one field.

## Dynamic endpointing

Dynamic mode scales the wait with the detector's confidence instead of using one
fixed number per turn. A confident end of turn returns near min. An ambiguous
trailing phrase stretches toward max. Fixed mode waits min on every turn and only
reaches max when the detector never fires.

Reach for it when the five caller types want different min delays and you cannot
pick one. That is the normal outcome on a clinic line: the digit case wants 0.8 s without an
audio detector, and a yes or no answer wants 0.3 s. The cost is one more parameter and a confidence
score you now depend on. Re-measure after turning it on.

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

Version pins and full mappings: [references/adapters.md](references/adapters.md).

### LiveKit Agents

Pinned 1.8.x, verified 11 September 2026. Set `turn_handling`. The legacy kwargs are deprecated and silently ignored when both forms are passed. Endpointing defaults are min 0.5 s and max 3.0 s, or 0.3 s and 2.5 s with a streaming detector. Turn limits live in `turn_handling["user_turn_limit"]`, off by default.
```python
from livekit.agents import AgentSession, TurnHandlingOptions, inference
session = AgentSession(turn_handling=TurnHandlingOptions(
    turn_detection=inference.TurnDetector(),
    endpointing={"min_delay": 0.3, "max_delay": 2.5}))
```
Docs: https://docs.livekit.io/agents/build/turns/

### Pipecat

Pipecat 1.0, unversioned docs, checked 11 September 2026. Turn detection attaches to the user aggregator, not to the transport or the worker. The local smart-turn analyzer is already the default stop strategy, paired with a VAD at `stop_secs=0.2`. `SmartTurnParams` defaults: `stop_secs` 3.0, `pre_speech_ms` 500.0, `max_duration_secs` 8.0. There is no single min and max endpointing pair. The snippet is the explicit form of that default, so you can see where the analyzer attaches.
```python
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies
strategies = UserTurnStrategies(stop=[TurnAnalyzerUserTurnStopStrategy(
    turn_analyzer=LocalSmartTurnAnalyzerV3())])
```
Docs: https://docs.pipecat.ai/api-reference/server/utilities/turn-detection/smart-turn-overview

### Vapi

Unversioned docs, checked 11 September 2026. Endpointing precedence, highest first: `customEndpointingRules`, `smartEndpointingPlan`, `transcriptionEndpointingPlan`, the transcriber's built-in endpointing.
`startSpeakingPlan.waitSeconds` default 0.4, min 0, max 5. It is a floor, not a ceiling: pipeline latency adds to it.
`transcriptionEndpointingPlan`: `onPunctuationSeconds` 0.1, `onNoPunctuationSeconds` 1.5, `onNumberSeconds` 0.5 in the machine-readable default and 0.4 in the prose of the same spec. Verify against current docs.
`customEndpointingRules` is the digit-case knob: a regex rule with `timeoutSeconds` up to 15 s, matched while the caller enumerates numbers.
Docs: https://docs.vapi.ai/customization/speech-configuration

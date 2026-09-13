---
name: voice-interruptions
description: Handle callers who speak while the agent is speaking. Covers barge-in, interruption modes, false interruptions from coughs and backchannels, resuming after a false stop, uninterruptible segments such as the read-back gate before any write, and whether filler speech during tool calls stays interruptible. Use when the agent stops for mm-hm and background noise, when it will not stop when told to, when a confirmation gets cut off, or when tuning barge-in sensitivity.
license: MIT
metadata:
  author: mahimairaja
  version: "0.1.0"
  category: voice-ai
---

# Voice Interruptions

This skill decides when the agent stops talking because the caller started. It sets
the barge-in floors, the resume rule, and which sentences cannot be cut off.

## Use this when

- The agent stops mid-sentence every time the caller says "mm-hm".
- The agent keeps talking after the caller says "no, wait".
- A booking read-back gets cut off and the wrong slot is written.
- The agent stops, the caller says nothing, and the line is dead for seconds.
- A noisy or narrowband line triggers barge-in on background speech.

## Do not

- Do not make every utterance interruptible: a read-back gets cut and the write is wrong.
- Do not make nothing interruptible: the caller shouts at an agent that will not yield.
- Do not treat backchannels as interruptions. "Okay" and "mm-hm" mean keep going.
- Do not resume speech after a real interruption. The caller has already moved on.
- Do not let a read-back of a date, time, or number be cut off. That is the one gate.
- Do not raise the duration floor to fix a noisy line. The word floor is the right knob.
- Do not disable interruptions for a whole session to protect one sentence.

## The three questions

Every barge-in decision answers three questions, in this order. Most bugs are one
question answered in the wrong layer.

1. Was that speech? A speech gate answers this. A cough, a door, and line noise are
   not speech. This layer knows energy, not meaning.
2. Was it meant for me? The duration floor and the word floor answer this. A
   backchannel is speech aimed at nobody.
3. Should I stop? The utterance class answers this, not the audio. A read-back
   outranks the caller for the length of one sentence.

Stacks differ on which layer owns each question. Find all three before tuning one.

## Headline defaults

| knob | default | range | symptom when wrong |
| --- | --- | --- | --- |
| min interruption duration | 0.5 s | 0.3 to 0.8 s | too low: coughs stop the agent. too high: real interruptions feel ignored |
| min interruption words | 0 | 0 to 2 | raise to 2 on noisy or narrowband lines |
| false interruption timeout | 2.0 s, resume on | 1.5 to 3.0 s | agent stops, caller says nothing, dead air |
| read-back gate | confirmations uninterruptible | | everything else interruptible |

The full table, the backchannel list, and the classification table in full are in
[references/defaults.md](references/defaults.md).

## The read-back gate

**Anything the caller must confirm is uninterruptible. Everything else is interruptible.**

A confirmation is the last point at which a wrong value is cheap to fix. It is one
sentence, under 20 words, and it ends in a question the caller answers. Losing half of
it means the caller confirms a booking they never heard.

The failure it prevents: the agent starts the read-back, the caller says "yes" over
the word "Tuesday", and the write lands on the wrong slot. Nothing downstream catches
it, because the tool call succeeded.

Gate the sentence, not the session. Every other utterance stays interruptible.

## What is interruptible

| utterance | interruptible | why |
| --- | --- | --- |
| greeting | yes | repeat callers state their intent over it. Cutting them off wastes a turn |
| list of options | yes | the caller picks option two before option three is read |
| read-back of a booking | no | a cut read-back confirms a value the caller never heard |
| legal or consent notice | no | the record must show the whole notice played |
| filler during a tool call | yes | the caller may add a constraint while the tool runs |
| error message | yes | the caller often knows the fix before the sentence ends |
| closing | no | it carries the confirmation number and the callback line |

Three classes are uninterruptible: the read-back, the notice, and the closing that
carries the confirmation number. All three are short. If an uninterruptible utterance
runs past two sentences, split it. Do not widen the gate.

## False interruptions

A false interruption is a stop that no turn follows. The speech gate fired and the
agent went quiet. The caller then produced nothing usable: a cough, a car horn, a half
word, a backchannel that cleared the floor.

The resume rule: if no user turn arrives within 2.0 s of the stop, resume the
interrupted utterance from where it stopped. Below 1.5 s the agent resumes over a slow
caller. Above 3.0 s the dead air is worse than the interruption was.

Never resume after a real interruption. Once the caller has said something, the
interrupted sentence is stale. Resuming it replays an offer the caller already
rejected, and the caller now hears two agents. Resume covers silence, nothing else.

Log false interruption rate per 100 turns. Above 5, the duration floor is too low or
the line is noisy. That is a measurement, not a feeling.

## Backchannels

Backchannels are the caller saying "I am still here": mm-hm, okay, yeah, right,
uh-huh, sure. They are not interruptions. They arrive most often while the agent is
reading a list, which is exactly when stopping is most expensive.

Two ways to filter them.

- Duration floor. Stop only when speech lasts at least 0.5 s. Costs nothing, needs no
  transcription, and a typical backchannel is 0.2 to 0.4 s.
- Word floor. Stop only after 2 transcribed words. Catches a drawn-out single
  "okaaay" that clears the duration floor on length alone.

A floor of 2 blocks single-word backchannels and nothing more. "Got it" and "yeah
okay sure" clear it, so match those against a phrase list instead of raising the floor.
The word floor is also a trade: the agent cannot stop until transcription returns,
which adds 100 to 200 ms to every real barge-in. Raise it to 2 on noisy or narrowband lines
and leave it at 0 elsewhere. Do not raise both floors at once.

## The clinic example

Riverside Family Medicine, four physicians, inbound booking on the main line.

The BACKCHANNEL CASE. The agent offers three slots. The caller says "mm-hm" after the
first and "okay" after the second, each about 0.3 s. At a 0.5 s duration floor both
fall below the floor and the agent finishes the list. Drop the floor to 0.2 s and the
agent stops twice, loses its place, and re-reads slot one.

Same call on a narrowband line with hiss and handling noise. The duration floor no
longer separates speech from noise: a 0.6 s burst of hiss clears it. Raise the word
floor to 2 and leave the duration floor at 0.5 s. A word floor filters what produces
no transcribed words. A television or a second voice in the room produces words, and
only a phrase list or noise suppression upstream of the VAD filters those.

The READ-BACK CASE. The gate applies to one sentence in the flow, the one before
`book_appointment(patient_id, slot_id, appointment_type)`.

| step | utterance | gate |
| --- | --- | --- |
| 1 | "Thanks for calling Riverside Family Medicine. This call is recorded. How can I help?" | interruptible |
| 4 | the three offered slots | interruptible |
| 5 | "Dana Whitfield, Tuesday the fourteenth at three fifteen with Doctor Osei." | uninterruptible |
| 6 | "Your confirmation number is four seven two one." | uninterruptible |

`check_availability` is read only and its results stay interruptible. Only the
sentence that gates the write is protected, and only for its own duration.

Decide what your stack does with caller audio during an uninterruptible segment: some
discard it, some queue it as the next user turn. The two produce different calls. With
discard, the caller's "no, not Tuesday" is gone and the agent asks for a confirmation
it already has. With queue, the same words arrive as the answer to "is that correct?".
Read the setting before you ship the gate.

## Filler during tool calls

A tool call that passes 1.5 s needs a spoken filler, and that filler stays
interruptible. The timeout, the filler text, and the max tool steps belong to
[voice-function-tools](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-function-tools/SKILL.md). Nothing here changes them.

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

Vendor mappings in full, with a doc URL per claim, are in
[references/adapters.md](references/adapters.md).

### LiveKit Agents
1.8.x, verified 11 September 2026. Knobs live under `turn_handling["interruption"]`:
min_duration 0.5, min_words 0, resume_false_interruption True,
false_interruption_timeout 2.0. A legacy kwarg beside `turn_handling` is dropped in
silence. Inside a tool, call `context.disallow_interruptions()`.
```python
session = AgentSession(turn_handling={"interruption": {"min_words": 2}})
session.say("Tuesday the fourteenth at three fifteen.", allow_interruptions=False)
```
https://docs.livekit.io/agents/build/audio/

### Pipecat
1.0, unversioned docs, checked 11 September 2026. Disabling interruptions does not
ignore the caller: speech over the bot is still transcribed and queued as a turn. A
real read-back gate needs a mute strategy, not an interruption setting.
```python
from pipecat.turns.user_mute import AlwaysUserMuteStrategy
from pipecat.turns.user_start import MinWordsUserTurnStartStrategy

start_strategy = MinWordsUserTurnStartStrategy(min_words=2)
```
https://docs.pipecat.ai/pipecat/fundamentals/interruptions

### Vapi
Unversioned docs, checked 11 September 2026. `stopSpeakingPlan` carries the floors:
`numWords` default 0 (max 10), `voiceSeconds` default 0.2 (used only when `numWords`
is 0), `backoffSeconds` default 1. `acknowledgementPhrases` never interrupt and
`interruptionPhrases` always do. Both ship with defaults that already cover the
backchannel list. `firstMessageInterruptionsEnabled` is a top-level assistant field
and gates the greeting. For a per-utterance uninterruptible flag on a read-back,
verify against current docs.
https://api.vapi.ai/api-json

# Interruption Defaults

The full interruption numbers table, the backchannel word list, and the
uninterruptible-utterance classification in full. SKILL.md carries only the headlines.

## Numbers

| knob | default | range | what it does | symptom when wrong |
| --- | --- | --- | --- | --- |
| interruptions enabled | on | on, off | master switch for the session | off: the caller talks at an agent that never yields |
| min interruption duration | 0.5 s | 0.3 to 0.8 s | speech must last this long before the agent stops | too low: coughs stop the agent. too high: real interruptions feel ignored |
| min interruption words | 0 | 0 to 2 | transcribed words required before the agent stops | too low on a noisy line: hiss and handling noise that transcribe to nothing stop the agent. too high: barge-in lags by the transcription delay |
| false interruption timeout | 2.0 s | 1.5 to 3.0 s | wait after a stop before resuming | too low: the agent resumes over a slow caller. too high: dead air |
| resume after false interruption | on | on, off | replay the rest of the interrupted utterance | off: the caller hears half an offer and nothing more |
| discard audio while uninterruptible | stack default | discard, queue | what happens to caller speech during a gated sentence | discard: a correction is lost. queue: it answers the wrong question |
| read-back gate | confirmations uninterruptible | | protects one sentence before a write | off: the caller confirms a value they never heard |
| interruption mode | stack default | audio gate, or audio plus transcript | which layer decides a stop | audio only on a noisy line: constant false stops |

Two floors, one change at a time. Raising both hides which one was the problem.

## Derived targets

| measure | target | how to read it |
| --- | --- | --- |
| false interruption rate | under 5 per 100 turns | above this the duration floor is too low or the line is noisy |
| ignored interruption rate | under 2 per 100 turns | the caller spoke over 1.0 s and the agent kept going |
| time from the floor clearing to agent silence | under 300 ms | measured from the moment the duration floor or word floor is satisfied, not from speech onset. Onset to silence adds the floor itself, 0.5 s, and 200 to 500 ms more at word floor 2 |
| read-back completion rate | 100 percent | any value below 100 means the gate is not applied to the write path |

## Backchannel word list

Treat every entry as a non-interruption. Match on the whole utterance, not on a
substring, so "no" inside "no problem" does not clear the floor.

| word | typical duration |
| --- | --- |
| mm-hm | 0.2 to 0.4 s |
| okay | 0.2 to 0.4 s |
| yeah | 0.2 to 0.3 s |
| right | 0.2 to 0.4 s |
| uh-huh | 0.3 to 0.5 s |
| sure | 0.2 to 0.4 s |
| got it | 0.3 to 0.5 s |
| I see | 0.3 to 0.5 s |

Their opposites clear both floors on their own: stop, wait, hold on, no, actually,
never mind. Keep that list short and explicit. Floors decide whether speech counts;
the gate decides whether the sentence yields, and a gated read-back still finishes.

## Uninterruptible-utterance classification, in full

| utterance | interruptible | why | what breaks if you get it wrong |
| --- | --- | --- | --- |
| greeting | yes | repeat callers open with their intent | the caller repeats themselves and the call gains a turn |
| identity question | yes | the caller often answers before the question ends | the caller waits through a question they already answered |
| list of options | yes | the caller picks option two before option three is read | the agent reads three slots to a caller who chose the first |
| filler during a tool call | yes | the caller may add a constraint while the tool runs | a late constraint arrives after the write |
| clarifying question | yes | short, and the answer is the point | none, this is the cheap case |
| error message | yes | the caller often knows the fix already | the caller waits through an explanation they do not need |
| read-back of a booking | no | a cut read-back confirms a value the caller never heard | the wrong slot is written and nothing downstream catches it |
| read-back of a number or date | no | digits carry no redundancy, half a number is a different number | the wrong phone number gets the confirmation text |
| legal or consent notice | no | the record must show the whole notice played | the recording shows a partial notice |
| closing with a confirmation number | no | it is the caller's only reference after the call | the caller calls back to ask what they just booked |

Everything not listed is interruptible. Add a class to the uninterruptible side only
with a written reason, and keep each one under two sentences.

## Tuning order

1. Measure the false interruption rate over at least 50 turns on a real phone call.
2. Set the duration floor. Start at 0.5 s and move in 0.1 s steps.
3. Set the word floor. Leave it at 0 unless the line is noisy or narrowband.
4. Set the false interruption timeout to 2.0 s and turn resume on.
5. Apply the read-back gate to the sentence before each write, one sentence at a time.
6. Re-measure. A knob changed without a second measurement is a guess.

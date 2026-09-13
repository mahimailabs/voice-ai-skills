# Turn Taking Defaults

Every turn-taking number this repo uses, with its range, its symptom when wrong, and
recommended settings for each of the five caller types.

## The numbers

| knob | default | range | symptom when wrong |
| --- | --- | --- | --- |
| min endpointing delay | 0.5 s, or 0.3 s with an audio turn detector | 0.3 to 1.0 s | too low: agent cuts off the digit case. too high: agent feels slow |
| max endpointing delay | 3.0 s, or 2.5 s with an audio turn detector | 1.5 to 6.0 s | too low: long pausers get interrupted. too high: dead air after a trailing "um" |
| VAD min silence | 0.2 to 0.5 s | | this is a speech-versus-noise gate, never an end-of-turn signal |
| user turn limits (max words, max duration) | off | | turn on only for scripted or adversarial calls |

Two notes on that table.

Treat 0.3 s as the floor. Below it the endpointing delay is shorter than the VAD
silence window and the transcript finalization time, so it buys nothing and the turn
commits on a partial transcript. The floor does not protect a digit read: a 0.6 s gap
between digit groups ends the turn at 0.3 s and at 0.5 s alike. The audio turn
detector is what protects the digit read.

The max delay range reaches 6.0 s. Above 3.0 s you are covering for a detector that
is not firing. Fix the detector instead, and write down why if you still need 4 s.

## Detector selection

| detector | min delay | max delay | when to pick it |
| --- | --- | --- | --- |
| VAD silence only | not viable alone | not viable alone | never, on a phone line |
| transcription endpoint | 0.5 s | 3.0 s | the STT provider is the only signal you have |
| semantic text model | 0.5 s | 3.0 s | text-first stacks, and you accept the transcription delay |
| audio turn model | 0.3 s | 2.5 s | default for phone calls. Prosody survives narrowband audio |

A VAD runs in front of every row. It gates when the detector runs. It does not decide.

## Per-caller-type settings

Start from the audio turn detector row above, then apply the change in this table.
Verify each with a recorded call, not a text run.

| caller type | min delay | max delay | mode | other changes |
| --- | --- | --- | --- | --- |
| fast talker | 0.3 s | 2.5 s | dynamic | preemptive generation on |
| list reader | 0.3 s | 3.0 s | dynamic | detector must see an incomplete phrase as incomplete |
| number reader | 0.3 s with an audio detector, 0.8 s without | 2.5 s | dynamic | a longer per-field timeout while digits are being read |
| long pauser | 0.8 s | 3.0 s | fixed | leave max at 3.0 s so a trailing "um" still lands |
| non-native speaker | 0.6 s | 3.0 s | dynamic | a multilingual detector, then re-measure end-of-turn delay |

The number reader row is the only one where the detector choice changes the min delay.
That is the whole argument for an audio turn detector on a clinic line.

## User turn limits

Off by default. Both limits are hard cuts, and a real caller who is mid-sentence at
the limit gets cut. Turn them on for scripted flows and for adversarial or abusive
calls, where a bounded turn is the point.

| limit | suggested value when on | what it protects |
| --- | --- | --- |
| max words | 100 | a caller who never stops, or a hot mic on an open line |
| max duration | 30 s | a stuck stream that never emits a silence |

## Measuring

Measure end-of-turn delay as the gap from the caller's last word to the moment the
turn is declared over, on a real phone call. Take 50 turns, report p50 and p95. The
caller feels that number plus everything after it, up to the first agent audio byte.

A 200 ms change in min delay moves p50 by roughly 200 ms on every turn that ends
with a clean stop. It moves nothing on turns that run out to max delay. If your p95
does not move when you change min, the detector is not firing and max is doing the
work. Full latency method: [voice-latency-budget](../../voice-latency-budget/SKILL.md).

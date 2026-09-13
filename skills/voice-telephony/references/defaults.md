# Telephony Defaults

The full telephony numbers table. Every knob carries a default, a range, and the
symptom you see when it is wrong. SKILL.md carries only the headline values.

## Call setup and answer

| knob | default | range | symptom when wrong |
| --- | --- | --- | --- |
| greeting delay after answer, inbound | 0.5 s | 0.3 to 1.0 s | too low: the first word is clipped while the media path settles. too high: the caller says "hello?" first |
| greeting delay after answer, outbound | not a timer, wait for detection | | any fixed delay outbound talks over a voicemail greeting |
| ring timeout, outbound dial | 30 s | 20 to 45 s | too low: you drop calls that answer on the sixth ring. too high: a worker is held open for a dead number |
| ring timeout, transfer leg | 30 s | 20 to 45 s | too low: the destination never gets to the phone. too high: the caller holds with no update |
| max call duration | 10 min | 5 to 20 min | no cap: a stuck session bills until the carrier drops it |
| post-message silence before hangup | 5 s | 3 to 8 s | too low: a person who was reaching for a pen is cut off. too high: seconds of silence on the recording |

## Answering machine detection

| knob | default | range | symptom when wrong |
| --- | --- | --- | --- |
| decision window | 3.0 s | 2.0 to 5.0 s | too low: a slow "hello, hello?" classifies as a machine. too high: a person hears three seconds of dead air and hangs up |
| hard cap on the detector | 20 s | 10 to 20 s | without a cap the call sits silent until the carrier tears it down |
| silence that ends a human greeting | 0.5 s | 0.3 to 1.0 s | too high: every human answer looks like a machine pause |
| silence that ends a machine greeting | 1.5 s | 1.0 to 2.5 s | too low: a voicemail greeting with a pause in it classifies twice |
| no-speech timeout | 10 s | 5 to 15 s | a silent answer never resolves and the agent waits out the hard cap |
| runs per call | once, on the first utterance | | continuous detection reclassifies mid-call and mutes the agent at random |

The detector must hold speech playout while it runs. An agent that greets in parallel
with detection has no detection at all.

## DTMF

| knob | default | range | symptom when wrong |
| --- | --- | --- | --- |
| tone duration | 0.1 s | 0.08 to 0.2 s | too short: the menu misses the digit entirely |
| inter-digit gap | 0.15 s | 0.1 to 0.3 s | too low: the menu merges two digits. too high: the menu times out mid-string |
| pause before the first digit | 1.0 s | 0.5 to 2.0 s | too low: the digit lands while the menu prompt is still playing and is ignored |
| transport | out of band, RTP telephone events | | in-band tones survive G.711 but not a compressed codec on some hop, nor noise suppression on your own output |
| speech gate while sending | on for the whole string | | off: the agent narrates over its own tones and the menu matches neither |

## Outbound retry policy

| knob | default | range | symptom when wrong |
| --- | --- | --- | --- |
| attempts per number per day | 2 | 1 to 3 | above 3 the campaign reads as harassment and the number gets flagged |
| backoff between attempts | 1 h, then 4 h | 30 min to 6 h | too low: two calls inside an hour. too high: the reminder lands after the appointment |
| retry on machine unavailable | yes, next window | | retrying immediately hits the same full mailbox |
| retry on voicemail with a message left | no | | a second message on the same day is a complaint |
| retry on human, call completed | no | | any retry here is a bug, not a policy |
| dial window, weekdays | 9am to 8pm, callee local time | narrower, never wider | a window read from the server clock calls at 6am three time zones away |
| dial window, weekends | 10am to 6pm, callee local time | narrower, never wider | some jurisdictions set a shorter weekend window, and one window for seven days breaks it |

## Narrowband audio

| knob | value | note |
| --- | --- | --- |
| sample rate | 8 kHz | assume narrowband. The codec is negotiated per call, and a wideband path (G.722, AMR-WB, Opus) exists only if you have seen it negotiated end to end on a real call. Most PSTN interconnects transcode to G.711 |
| passband | roughly 300 to 3400 Hz | fricatives lose the energy that separates them |
| STT model | telephony or 8 kHz trained | a wideband model on resampled audio loses digits and names |
| min interruption words | 2 | raised from the default of 0, because line hiss and handling noise clear a duration floor here and produce no words |
| number confirmation | always read back | digit confusions rise on a narrow line |

Upsampling to 16 kHz before the STT does not restore anything. The information above
3400 Hz was never carried.

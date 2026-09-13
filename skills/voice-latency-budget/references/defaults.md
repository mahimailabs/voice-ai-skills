# Latency defaults

The full per-stage budget for all three pipeline shapes, at p50 and p95, plus the six
places milliseconds hide and what each one typically costs.

## How to read these

All values are milliseconds, measured on a real phone call over PSTN, not on Wi-Fi
from a laptop. p50 ceilings come from the shared numbers canon. The p95 ceiling is
twice the p50 ceiling. A stage inside its p50 ceiling but above its p95 ceiling is a
tail problem, not a tuning problem: look at retries, cold connections, and jitter.

A stage marked "folded into the model" is not separately observable in that shape. Do
not report a made-up value for it. Report the end-to-end number and say which stages
are unobservable.

## Cascade

| stage | p50 ceiling | p95 ceiling | knob that moves it |
| --- | --- | --- | --- |
| end-of-turn delay | 300 to 500 | 1000 | endpointing min delay, turn detector choice |
| transcription delay | 100 to 200 | 400 | streaming transcription, provider region |
| LLM time to first token | 200 to 400 | 800 | preemptive generation, prompt size, model size |
| TTS time to first byte | 100 to 300 | 600 | streaming synthesis, warm connection, region |
| end to end | 800 | 1600 | all of the above, in the order-of-fixes order |

## Speech to speech

| stage | p50 ceiling | p95 ceiling | knob that moves it |
| --- | --- | --- | --- |
| end-of-turn delay | 300 | 600 | the model's own turn settings |
| transcription delay | folded into the model | folded into the model | none |
| LLM time to first token | folded into the model | folded into the model | none |
| TTS time to first byte | folded into the model | folded into the model | none |
| end to end | 500 | 1000 | region choice, prompt size, session setup |

## Full duplex

| stage | p50 ceiling | p95 ceiling | knob that moves it |
| --- | --- | --- | --- |
| end-of-turn delay | not applicable | not applicable | the model owns turn taking |
| transcription delay | folded into the model | folded into the model | none |
| LLM time to first token | 700 for the delegated backend model | 1400 | backend model size, tool latency |
| TTS time to first byte | folded into the model | folded into the model | none |
| end to end | 300 | 600 | region choice, startup context size |

## Where the milliseconds hide

| hiding place | typical cost | how to confirm it |
| --- | --- | --- |
| cross-region hop | 80 to 150 ms per round trip | compare same-region and cross-region runs of 50 turns |
| cold synthesis connection | 200 to 400 ms, first utterance only | compare turn 1 time to first byte against turns 2 to 10 |
| non-streaming synthesis | 300 to 900 ms | check whether time to first byte scales with reply length |
| prompt size | 100 to 300 ms per extra 10,000 tokens | halve the prompt, re-run 50 turns, diff time to first token |
| tool round trip | 200 to 1500 ms | bucket turns with a tool call apart from turns without |
| jitter buffer and codec | 40 to 100 ms each way | compare a PSTN call against a WebRTC call, same agent |

Every figure in this table is a starting estimate. Replace each one with a measured
value from your own stack before you use it in a budget.

## Order of fixes, with expected gain

| step | fix | expected gain | cost |
| --- | --- | --- | --- |
| 1 | endpointing min delay | 200 to 400 ms | risk of cutting off slow and digit-reading callers |
| 2 | preemptive generation | 200 to 300 ms | wasted model calls on revised turns |
| 3 | streaming TTS | 200 to 600 ms | reply must be split at sentence boundaries |
| 4 | region co-location | 80 to 150 ms per hop | provider choice is constrained by region |
| 5 | smaller model | 100 to 300 ms | accuracy, so pair it with an eval run |

## Measurement rules

| rule | value | why |
| --- | --- | --- |
| percentiles reported | p50 and p95 | one number hides the turn that lost the caller |
| minimum sample | 50 turns | below that, p95 is a single sample |
| transport | real phone call | Wi-Fi under-reports jitter buffer and codec cost |
| bucketing | tool turns apart from non-tool turns | mixing them hides both distributions |
| re-measure | after every single fix | fixes interact, and one can expose another |
| logging | per-turn stage timings plus a turn id | a slow p95 turn must be replayable |

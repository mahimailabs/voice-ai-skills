# Voice agent review checklist

The 40 scored items, eight groups of five, one point each. Every pass condition is
checkable by reading code, config, the CI schedule, or a measurement run committed to
the repository. Anything you cannot find in one of those four places fails. Three
latency items need that committed run, because no amount of reading code produces a
measured number: say where the run lives, or score them zero.

## 1. Pipeline choice

| item | pass condition | skill to read on failure |
| --- | --- | --- |
| shape is declared | one line next to the session construction names the shape: cascade, speech-to-speech, half-cascade, or full-duplex | [voice-pipeline-choice](../../voice-pipeline-choice/SKILL.md) |
| exact wording is protected | every string the caller must hear verbatim is spoken by a text-to-speech stage the code controls | [voice-pipeline-choice](../../voice-pipeline-choice/SKILL.md) |
| voice is pinned | the voice is selected by an explicit identifier in config, not chosen by the model at runtime | [voice-pipeline-choice](../../voice-pipeline-choice/SKILL.md) |
| provider seams exist | the speech, language, and voice stages are named in one place, so no provider identifier appears at the session construction site | [voice-pipeline-choice](../../voice-pipeline-choice/SKILL.md) |
| cost per minute is written down | a per-minute figure exists for the chosen shape, with a date and a re-check note | [voice-pipeline-choice](../../voice-pipeline-choice/SKILL.md) |

## 2. Turn-taking

| item | pass condition | skill to read on failure |
| --- | --- | --- |
| the turn decision is not the voice gate | the config names a transcription endpoint, a semantic model, or an audio turn model as the decider | [voice-turn-taking](../../voice-turn-taking/SKILL.md) |
| a voice activity gate sits in front | a voice activity detector is configured and not disabled, whatever the decider is | [voice-turn-taking](../../voice-turn-taking/SKILL.md) |
| min endpointing delay is explicit | the value is set in config and is 0.3 s or higher | [voice-turn-taking](../../voice-turn-taking/SKILL.md) |
| max endpointing delay is explicit | the value is set in config and is 3.0 s or lower, or a comment states the reason it is higher | [voice-turn-taking](../../voice-turn-taking/SKILL.md) |
| turn limits are off by default | max words and max duration are unset, or a comment names the scripted or adversarial call that needs them | [voice-turn-taking](../../voice-turn-taking/SKILL.md) |

## 3. Interruptions

| item | pass condition | skill to read on failure |
| --- | --- | --- |
| the read-back is uninterruptible | the utterance that reads back a booking is marked uninterruptible at the call site | [voice-interruptions](../../voice-interruptions/SKILL.md) |
| interruptions stay on elsewhere | the session enables interruptions, and only named utterances opt out | [voice-interruptions](../../voice-interruptions/SKILL.md) |
| min interruption duration is set | the value is 0.5 s, or between 0.3 s and 0.8 s with a comment | [voice-interruptions](../../voice-interruptions/SKILL.md) |
| min interruption words matches the line | the value is set explicitly, and it is 2 where a PSTN or SIP path exists, 0 where the only path is wideband | [voice-interruptions](../../voice-interruptions/SKILL.md) |
| false interruptions resume | a false interruption timeout of 2.0 s is set and resume is on, so a cough does not end the turn | [voice-interruptions](../../voice-interruptions/SKILL.md) |

## 4. Latency

| item | pass condition | skill to read on failure |
| --- | --- | --- |
| the five timings are logged | transcription delay, end-of-turn delay, first token, first audio byte, and end to end are recorded per turn | [voice-latency-budget](../../voice-latency-budget/SKILL.md) |
| p50 and p95 are both reported | the reported numbers are percentiles from a turn set, not one average | [voice-latency-budget](../../voice-latency-budget/SKILL.md) |
| the measurement is a phone call | the recorded run names the telephony path and covers at least 50 turns | [voice-latency-budget](../../voice-latency-budget/SKILL.md) |
| stages are co-located | the language stage and the voice stage are pinned to the same region in config | [voice-latency-budget](../../voice-latency-budget/SKILL.md) |
| the voice stage streams | no code awaits a complete synthesis before playback: no full audio buffer, no complete file written to the transport | [voice-latency-budget](../../voice-latency-budget/SKILL.md) |

## 5. Prompting

| item | pass condition | skill to read on failure |
| --- | --- | --- |
| spoken output is enforced | the prompt forbids markdown, headers, bullet lists, and symbols in the spoken output | [voice-prompting](../../voice-prompting/SKILL.md) |
| numbers are written as speech | dates, times, money, and codes appear in the prompt as words, the way they are said | [voice-prompting](../../voice-prompting/SKILL.md) |
| sentence length is capped | the prompt states a per-sentence cap of 20 words or fewer and one idea per sentence | [voice-prompting](../../voice-prompting/SKILL.md) |
| persona and task are separate blocks | persona holds tone only, and the tool policy lives outside it | [voice-prompting](../../voice-prompting/SKILL.md) |
| a confirmation block exists | the prompt names the fields read back before a write and the exact confirmation question | [voice-prompting](../../voice-prompting/SKILL.md) |

## 6. Tools

| item | pass condition | skill to read on failure |
| --- | --- | --- |
| writes are gated by a read-back | every side-effecting tool either refuses to run without a confirmation argument, or the prompt orders a read-back and a spoken yes before the call, and the read-back utterance is uninterruptible | [voice-function-tools](../../voice-function-tools/SKILL.md) |
| every tool has a deadline | a 5 s timeout is set in the framework or on the client, with a sentence the agent says when it expires | [voice-function-tools](../../voice-function-tools/SKILL.md) |
| the line does not go silent | every tool that can exceed 1.5 s has a spoken filler, set to play once rather than on a loop | [voice-function-tools](../../voice-function-tools/SKILL.md) |
| tool steps are capped | the maximum consecutive tool calls per turn is 3 or lower | [voice-function-tools](../../voice-function-tools/SKILL.md) |
| returns and context are bounded | tools return a sentence or a small typed object, and history is the the full history to a token budget, then a summary of the oldest turns with a stable prefix | [voice-function-tools](../../voice-function-tools/SKILL.md) |

## 7. Telephony

| item | pass condition | skill to read on failure |
| --- | --- | --- |
| outbound detects the answerer first | answering machine detection completes before the first agent utterance on every outbound call | [voice-telephony](../../voice-telephony/SKILL.md) |
| uncertain is handled machine-safe | the uncertain branch says one short self-contained line and waits, and does not open a conversation | [voice-telephony](../../voice-telephony/SKILL.md) |
| digits go through signaling | tones are sent on the signaling path, not spoken into the audio, and the agent is silent while sending | [voice-telephony](../../voice-telephony/SKILL.md) |
| transfers are typed | each transfer target declares cold or warm, and every warm transfer has a hold experience | [voice-telephony](../../voice-telephony/SKILL.md) |
| consent and dialing windows are code | recording is announced before capture starts, and outbound dialing checks a time-of-day window | [voice-telephony](../../voice-telephony/SKILL.md) |

## 8. Evals

| item | pass condition | skill to read on failure |
| --- | --- | --- |
| the suite covers failure paths | at least ten scenarios exist, and they include identity, refusal, timeout, and voicemail cases | [voice-agent-evals](../../voice-agent-evals/SKILL.md) |
| the assert and judge split holds | anything with one correct answer is asserted, and judges cover only matters of degree | [voice-agent-evals](../../voice-agent-evals/SKILL.md) |
| audio runs are on the release gate | the text suite runs on every commit, and the audio suite runs nightly and before release | [voice-agent-evals](../../voice-agent-evals/SKILL.md) |
| latency rides with pass rate | the same run reports p50 and p95 next to the pass rate | [voice-agent-evals](../../voice-agent-evals/SKILL.md) |
| the target is written down | a pass-rate target is recorded against the maturity curve, and the judge model is not the agent model | [voice-agent-evals](../../voice-agent-evals/SKILL.md) |

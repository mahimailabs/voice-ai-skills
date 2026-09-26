# Voice agent review: Riverside Family Medicine clinic agent, LiveKit path (examples/clinic-agent/livekit_agent.py)

- Date: 2026-09-26
- Reviewer: Claude (voice-agent-review skill)
- Commit: aea7d7b
- Surface reviewed: neither inbound nor outbound phone line. The only path is a LiveKit WebRTC room (README.md:100). The Pipecat path (pipecat_agent.py) is not scored here and needs its own report if it ships.
- Cap: pilot, capped by 1 hard fail

## Score

| group | score | out of |
| --- | --- | --- |
| pipeline choice | 3 | 5 |
| turn-taking | 5 | 5 |
| interruptions | 4 | 5 |
| latency | 2 | 5 |
| prompting | 5 | 5 |
| tools | 4 | 5 |
| telephony | 0 | 5 |
| evals | 0 | 5 |
| total | 23 | 40 |

Band: pilot

## Hard fails

| hard fail | present | evidence |
| --- | --- | --- |
| no read-back gate on a write | no | none found. book_appointment is two-phase (clinic.py:179-199), and the read-back plays with allow_interruptions=False and must finish uninterrupted before the gate arms (livekit_agent.py:40-48) |
| no audio tests | yes | .github/workflows/validate.yml:17-18 runs only text unit tests; README.md:100-101 states there is no voice/model eval suite |
| no latency measurement | no | none found. Five named timings are logged per message (clinic.py:217, livekit_agent.py:118-122), and scripts/metrics_report.py reports p50 and p95 |
| uncertain answering machine result treated as human | no | not applicable, no phone path and no outbound calling (README.md:100) |

Any yes caps the band at pilot, whatever the total.

## The three fixes to do first

1. Add an audio scenario suite for the clinic flow (at least ten scenarios, including identity, refusal, timeout, and voicemail) and run it nightly and before release next to the text job (.github/workflows/validate.yml:17-18). Severity: hard fail.
   Cost: one code path.
2. Commit a measured run of at least 50 turns with p50 and p95 per timing, produced from the voice_metrics logs by scripts/metrics_report.py (livekit_agent.py:118-122). Region co-location stays unranked until this run shows whether a cross-region hop exists. Severity: measurable. Cost: one code path.
3. Set min interruption words to 0, because the only path is a wideband WebRTC room. At 2, a one-word "wait" or "no" does not stop the agent (livekit_agent.py:112). Severity: annoying. Cost: one config value.

## Findings by group

### Pipeline choice 3/5
- PASS shape is declared: "cascade, because dates and codes must be exact" sits on the session construction (livekit_agent.py:102).
- PASS exact wording is protected: the read-back and the confirmation code are fixed strings sent to TTS through session.say (clinic.py:195, clinic.py:202, livekit_agent.py:40).
- PASS voice is pinned: voice="Ashley" on the TTS stage (livekit_agent.py:105).
- FAIL provider seams exist (livekit_agent.py:103-105): provider and model identifiers ("deepgram/nova-3", "google/gemma-4-31b-it", "inworld/inworld-tts-2") are written inline at the AgentSession construction site. Read voice-pipeline-choice.
- FAIL cost per minute is written down (examples/clinic-agent/README.md): the example records no per-minute figure, date, or re-check note. Read voice-pipeline-choice.

### Turn-taking 5/5
- PASS the turn decision is not the voice gate: turn_detection=inference.TurnDetector(), an audio turn model (livekit_agent.py:109).
- PASS a voice activity gate sits in front: no vad=None override in the session (livekit_agent.py:101-116). The pinned 1.8.x adapter records a bundled Silero VAD as the default (skills/voice-turn-taking/references/adapters.md:51).
- PASS min endpointing delay is explicit: min_delay 0.3 (livekit_agent.py:110).
- PASS max endpointing delay is explicit: max_delay 2.5 (livekit_agent.py:110).
- PASS turn limits are off by default: no user_turn_limit is set (livekit_agent.py:107-115).

### Interruptions 4/5
- PASS the read-back is uninterruptible: speak(..., True) at the call site (clinic.py:195, clinic.py:202) maps to allow_interruptions=False (livekit_agent.py:40).
- PASS interruptions stay on elsewhere: the session keeps interruption enabled (livekit_agent.py:112), and the filler opts in with speak(..., False) (clinic.py:124).
- PASS min interruption duration is set: min_duration 0.5 (livekit_agent.py:112).
- FAIL min interruption words matches the line (livekit_agent.py:111-112): min_words is 2 with a "phone line" comment, but this path has no PSTN or SIP leg. It is wideband only, so the value should be 0. Read voice-interruptions.
- PASS false interruptions resume: false_interruption_timeout 2.0 (livekit_agent.py:112). Resume stays at the 1.8.x default of on, and the code does not override it (skills/voice-interruptions/SKILL.md:184-185).

### Latency 2/5
- PASS the five timings are logged: transcription_delay, end_of_turn_delay, llm_node_ttft, tts_node_ttfb, and e2e_latency are logged per message. Missing values stay null (clinic.py:217-219, livekit_agent.py:118-122).
- FAIL p50 and p95 are both reported (examples/clinic-agent/README.md:88-91): the percentile tool exists (scripts/metrics_report.py), but no committed run reports any numbers. Read voice-latency-budget.
- FAIL the measurement is a phone call (examples/clinic-agent/README.md:100): no committed run exists, and there is no telephony path to measure. Read voice-latency-budget.
- FAIL stages are co-located (livekit_agent.py:103-105): no region is pinned for the language or voice stage. Read voice-latency-budget.
- PASS the voice stage streams: session.say hands text to the streaming TTS stage. No code buffers a full synthesis or writes a file (livekit_agent.py:40).

### Prompting 5/5
- PASS spoken output is enforced: "No markdown, lists, symbols, or emoji in spoken replies" (clinic.py:17-18).
- PASS numbers are written as speech: "Say three fifteen in the afternoon. Read codes digit by digit." No digit-form dates, times, or money appear in the prompt (clinic.py:19-20).
- PASS sentence length is capped: "One idea per sentence, under twenty words" (clinic.py:19).
- PASS persona and task are separate blocks: PERSONA holds role, tone, and refusals (clinic.py:22-24). Tool policy is in TASK and CONFIRMATION (clinic.py:25-35).
- PASS a confirmation block exists: CONFIRMATION names the two-call read-back, the fresh yes, and the correction rule, and the tool speaks the exact question "... Is that right?" (clinic.py:29-35, clinic.py:195).

### Tools 4/5
- PASS writes are gated by a read-back: the first call only speaks the protected proposal. A write needs a new allowlisted yes after an uninterrupted playout (clinic.py:97-105, clinic.py:179-199, livekit_agent.py:40-48). Preemptive generation is off (livekit_agent.py:114).
- PASS every tool has a deadline: 5 s asyncio.wait_for on every backend call (clinic.py:14, clinic.py:128), with a spoken line when it expires (clinic.py:143, clinic.py:158, clinic.py:187, clinic.py:210).
- PASS the line does not go silent: one interruptible "Let me check that." after 1.5 s, cancelled when the call returns (clinic.py:15, clinic.py:122-132).
- PASS tool steps are capped: max_tool_steps=3 (livekit_agent.py:106), also enforced per caller turn (clinic.py:111-113).
- FAIL returns and context are bounded (examples/clinic-agent/README.md:57-58): returns are small typed dicts (clinic.py:146, clinic.py:160-163), but history has no token budget and no summary of the oldest turns. The session construction sets neither (livekit_agent.py:101-116). Read voice-function-tools.

### Telephony 0/5
- FAIL outbound detects the answerer first (examples/clinic-agent/README.md:100): no phone path. Read voice-telephony.
- FAIL uncertain is handled machine-safe (examples/clinic-agent/README.md:100): no phone path, so there is no answering machine branch. Read voice-telephony.
- FAIL digits go through signaling (examples/clinic-agent/README.md:100): no phone path and no DTMF handling. Read voice-telephony.
- FAIL transfers are typed (examples/clinic-agent/README.md:100): no transfer targets. The prompt points callers to the front desk, but nothing connects them (clinic.py:26). Read voice-telephony.
- FAIL consent and dialing windows are code (examples/clinic-agent/README.md:42-43): recording is not implemented, and there is no announcement and no dialing window. Read voice-telephony.

### Evals 0/5
- FAIL the suite covers failure paths (tests/test_clinic.py:31-119): ten unit tests cover booking-rule ordering, wrong patient, and timeouts. They do not run the agent, and they have no refusal or voicemail case. Read voice-agent-evals.
- FAIL the assert and judge split holds (tests/test_clinic.py): no agent-level scenario exists. Behavior with one correct answer, such as refusing clinical advice or reading back the date of birth, is neither asserted nor judged. Read voice-agent-evals.
- FAIL audio runs are on the release gate (.github/workflows/validate.yml:17-18): CI runs text unit tests only, with no audio job, no nightly schedule, and no release gate. Read voice-agent-evals.
- FAIL latency rides with pass rate (.github/workflows/validate.yml:17-18): no run reports p50 and p95 next to a pass rate. Read voice-agent-evals.
- FAIL the target is written down (examples/clinic-agent/README.md:100-101): no pass-rate target, maturity-curve entry, or judge model is recorded. Read voice-agent-evals.

## Not scored

- p50 and p95 are both reported: no committed measurement run exists in the repository. Counted as a fail.
- the measurement is a phone call: no committed run and no telephony path. Counted as a fail.
- telephony, all five items: the agent has no phone path at all, and the skill scores that group zero. Counted as fails. Hard fail four is not applicable.
- evals, all five items: the example deliberately ships no agent eval suite (README.md:100-101). The regression tests check code contracts, not calls. Counted as fails.

# The clinic agent

One appointment-booking example on two stacks, with shared rules in [clinic.py](clinic.py).
It demonstrates six review areas: pipeline choice, turn-taking, interruptions,
latency instrumentation, prompting, and tools. Telephony and a voice eval suite are
intentionally outside this example.

## Run

From this directory, with Python 3.11 or later:

```sh
uv run --with "livekit-agents==1.8.1" --with python-dotenv livekit_agent.py dev
```

```sh
uv run --with "pipecat-ai[daily,deepgram,cartesia,openai,silero]==1.10.0" --with python-dotenv pipecat_agent.py
```

Provide a `.env` in this directory. LiveKit needs `LIVEKIT_URL`, `LIVEKIT_API_KEY`,
and `LIVEKIT_API_SECRET`; its inference stages use that account. Pipecat needs
`DAILY_ROOM_URL`, `DAILY_TOKEN`, `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY`,
`CARTESIA_VOICE_ID`, and `OPENAI_API_KEY`. These run commands use paid provider services.

The demo record is **Dana Whitfield, born March 4, 1980**. The date passed to the
lookup tool is `1980-03-04`. The calendar returns one fixed illustrative slot,
Tuesday, April 14 at 3:15 with Doctor Osei; it does not implement date-range search.
Replace `DemoSchedule` with your authenticated scheduling client and current data.
Name/DOB matching in this fixture is not patient authentication.

## Booking flow

1. `lookup_patient` returns a spoken status and a silent patient ID.
2. `check_availability` returns up to three spoken descriptions with silent slot IDs.
3. The first `book_appointment` call reads the chosen appointment aloud and writes nothing.
4. Only after completed playback and a new, explicitly recognized “yes” can a second
   call commit that same appointment. Corrections invalidate the pending confirmation.
5. The tool speaks the confirmation code directly. Repeated calls return the existing
   confirmation. An uncertain write is reconciled through a read, never another write.

The strict yes allowlist deliberately asks again for unfamiliar wording. Both
examples use the same three tools and four prompt blocks. Rescheduling, cancellation,
text confirmations, callbacks, and recording are not implemented or promised.

| Code | Behavior | Skill |
| --- | --- | --- |
| Explicit STT → LLM → TTS | Cascade for exact dates and codes | [pipeline choice](../../skills/voice-pipeline-choice/) |
| Audio turn detector and endpointing options | Configurable turn completion | [turn-taking](../../skills/voice-turn-taking/) |
| Word floor, protected `speak`, playback receipt | Ordinary replies can be interrupted; the read-back and code are protected | [interruptions](../../skills/voice-interruptions/) |
| `log_metrics`, `VoiceMetricsObserver` | Five named timing fields, preserving missing samples | [latency budget](../../skills/voice-latency-budget/) |
| `INSTRUCTIONS` in `clinic.py` | Spoken output, persona, task, confirmation | [prompting](../../skills/voice-prompting/) |
| `Clinic.call`, confirmation state, idempotency keys | Five-second backend deadline, filler after 1.5 seconds, three tool steps per caller turn | [function tools](../../skills/voice-function-tools/) |

LiveKit waits for an uninterruptible speech handle. Pipecat drops microphone audio
before STT during protected speech, mutes user frames at the aggregator, and waits
for the matching, uninterrupted assistant utterance to finish. Its context gate
updates confirmation state before passing a new user message to the LLM. The demo
retains full context; adding summarization requires stable user-turn identifiers.

Backend calls have five-second deadlines. Playback has a separate 30-second deadline;
Pipecat's outer booking-tool deadline is 45 seconds to allow playback and one
reconciliation. These are bounds, not promises of caller-perceived latency. Fillers
stay interruptible. Errors are short authored messages; backend exception text and
tool arguments are not written by application logs. LiveKit strips `lk.pii.*` fields;
Pipecat starts framework logging at INFO. Review all SDK/provider logging before
connecting real patient data.

## Timing logs

Both adapters emit JSON after the `voice_metrics ` marker, in **seconds**. Missing
measurements are `null`. No transcript or tool argument is included.

- **LiveKit:** native user-message transcription/turn delays and assistant-message
  TTFT/TTFB/E2E, keyed by message ID. User and assistant samples are separate;
  they are not falsely presented as one joined row.
- **Pipecat:** estimates keyed by local turn ID. Speech end is VAD stop minus its
  configured silence window; transcription delay ends at the final transcript;
  turn delay ends at the first LLM context frame; TTFT/TTFB use the first service
  TTFB metrics; E2E ends at the first transport bot-speaking event. This can include
  filler. Snapshots can arrive in several updates.

From the repository root:

```sh
python scripts/metrics_report.py call.log
```

The report merges snapshots and prints sample counts, missing counts, and nearest-rank
p50/p95 by scope and role. Do not mix the stacks' timing populations or treat server
playback as proof of what a caller heard. Real-call measurements and representative
audio scenarios remain required for release.

## Validation and limits

[Regression tests](../../tests/) cover confirmation ordering, interruption/cancellation,
timeouts before and after commitment, reconciliation, fillers, IDs, and SDK contracts.
SDK imports and fake-I/O checks use LiveKit Agents 1.8.1 and Pipecat 1.10.0.
[API verification sources](../../docs/sdk-verification.md) record what was checked.

Neither example is production ready. There is no telephony, durable storage, real
patient authentication, or voice/model eval suite. Idempotency is in-memory per call;
a real backend must persist keys and enforce them atomically across sessions. Live
provider calls and caller-device playback have not been certified by these tests.

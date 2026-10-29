# Voice agent spec template

Copy the block and fill every field. A field that does not apply says "not applicable"
and why. A field nobody can fill yet goes to Open questions with an owner and a date.
Each section maps to one group of the `voice-agent-review` checklist, so the review can
score the spec before any code exists.

```markdown
# Voice agent spec: <agent name>

- Status: <draft | in review | approved>
- Owner: <name>
- Date: <YYYY-MM-DD>
- Review: <not yet | n/40, band, review mode, date>

## Callers and job

- Who calls: <one sentence about the caller and why they call>
- Surfaces: <phone inbound | phone outbound | browser | app>, one line each
- Languages: <list, and whether callers switch mid-call>
- Success: <the outcome that counts as done, and how it is counted>
- Out of scope: <what the agent will not do, and where those callers go instead>

## Pipeline shape

- Shape: <cascade | speech-to-speech | half-cascade | full-duplex>, because <reason>
- Exact strings: <every string the caller must hear verbatim, and which stage speaks it>
- Voice: <pinned voice identifier, and where it is configured>
- Stages: <speech-to-text, language model, voice>, named in one place in config
- Cost per minute: <figure, date, re-check date>

## Turn-taking

- Decider: <transcription endpoint | semantic model | audio turn model>
- Voice activity gate: <detector, and that it stays on>
- Min endpointing delay: <value, 0.3 s or higher>, moves if <symptom>
- Max endpointing delay: <value, 3.0 s or lower, or the reason it is higher>
- Turn limits: <off, or the scripted call that needs them>

## Interruptions

- Uninterruptible utterances: <the read-back, and any other named line>
- Everything else: interruptible
- Min interruption duration: <value, 0.5 s default>
- Min interruption words: <2 on a phone path, 0 on wideband only>
- False interruptions: <resume after 2.0 s, or the reason not to>

## Latency budget

| stage | p50 target | p95 target |
| --- | --- | --- |
| transcription delay | <ms> | <ms> |
| end-of-turn delay | <ms> | <ms> |
| first token | <ms> | <ms> |
| first audio byte | <ms> | <ms> |
| end to end | <ms> | <ms> |

- Measurement run: <telephony path, at least 50 turns, where the run will be committed>
- Regions: <language and voice stages in the same region>
- Streaming: <the voice stage streams; nothing waits for a full synthesis>
- Tool turns: reported apart from turns with no tool call

## Prompt

- Blocks: persona (tone only), task, tool policy, spoken-output rules, confirmation
- Spoken output: no markdown, headers, lists, or symbols
- Numbers: dates, times, money, and codes written as words in every example
- Sentence cap: <20 words or fewer>, one idea per sentence
- Confirmation: <the fields read back, and the exact question>

## Tools

| tool | writes? | deadline | filler at 1.5 s | read-back fields | returns |
| --- | --- | --- | --- | --- | --- |
| <name> | <yes/no> | <5 s> | <line, played once> | <fields, or none> | <one sentence or small typed object> |

- Write gate: <how a write refuses to run without a confirmed read-back>
- Timeout outcome: <what the agent says, and how an uncertain write is reconciled>
- Max tool calls per turn: <3 or fewer>
- Context budget: <token budget, and how old turns are summarized>

## Telephony

- Answering machine detection: <before the first utterance on outbound, or not applicable>
- Uncertain result: <one short self-contained line, then wait>
- Transfers: <each target, cold or warm, and the hold experience for warm>
- Digits: <sent on the signaling path, agent silent while sending>
- Consent: <recording announcement in the first utterance>
- Dialing window: <time-of-day rule in the callee's time zone, or not applicable>
- Narrowband: <8 kHz path tested for speech-to-text and floors>

## Evals

- Scenarios: <at least ten, including identity, refusal, timeout, voicemail>
- Asserted: <everything with one correct answer>
- Judged: <only matters of degree>, by <a model that is not the agent's model>
- Gate: <text suite on every commit, audio suite nightly and before release>
- Latency: <p50 and p95 reported from the same run as the pass rate>
- Target: <pass rate to launch, and to leave pilot>

## Decisions log

| decision | rejected | why | revisit when |
| --- | --- | --- | --- |
| <choice> | <alternatives> | <reason, with a number where one exists> | <date or symptom> |

## Open questions

| question | owner | due |
| --- | --- | --- |
| <question> | <name> | <YYYY-MM-DD> |
```

Rules for filling it in. Write the decision, not the discussion. Keep each field to one
line where you can. Move SDK method names out of the spec and into the code; name the
behavior instead. When the review fails an item, change the field or add a row to the
decisions log, never both silently.

---
name: voice-agent-spec
description: Write a design spec for a voice agent before any code, with one section for each production review group, so it can be scored and fixed while changes are still cheap. Covers the questions that decide the pipeline shape, a section-by-section draft with a sign-off after each, a fresh-reviewer score with voice-agent-review, and a decisions log. Use when starting a new voice agent, before a large change such as a new pipeline shape, a phone line, or outbound calling, or when someone asks for a design doc, PRD, or spec for a voice agent.
license: MIT
metadata:
  author: mahimairaja
  version: "0.1.0"
  category: voice-ai
---

# Voice Agent Spec

This skill writes the design of a voice agent down before anyone builds it, then has
it scored. A gap found in a spec costs one sentence. The same gap found on a live call
costs a wrong booking.

## Use this when

- A new voice agent is about to be built and nothing is written down yet.
- A change will cross a boundary: a new pipeline shape, a phone line, outbound calls,
  a write tool, or a second language.
- Someone asks for a design doc, PRD, or spec for a voice agent.
- A team disagrees about a default and needs one place to record the decision.

## Do not

- Do not copy a chat-bot PRD. It has no turn-taking, no read-back, and no phone line.
- Do not pick a provider before the shape. Exact wording decides the shape first.
- Do not leave a section as TBD. Write the open question, its owner, and a date.
- Do not write a number without a range and the symptom that would change it.
- Do not write SDK calls into the spec. They drift; the decision does not.
- Do not skip the eval plan. A spec with no scenarios cannot be called done.
- Do not review the spec in the session that wrote it. Use fresh reviewers.

## Ask these first

Ask one question at a time, and write each answer into the spec before the next. The
first two remove shapes before anyone argues about providers.

1. Must the caller hear any string exactly: a date, an amount, a code, a legal line?
2. Where do callers reach it: a phone number, a browser, an app, or more than one?
3. Who speaks first: does it answer calls, place them, or both?
4. What does it change in the world: which tools book, charge, send, or cancel?
5. Which languages, and do callers switch mid-call?
6. What end-to-end delay, at p50 and p95, would the caller call slow?
7. How will you know it works: which ten calls must it get right before launch?

If the first answer is yes, the shape is a cascade or a half-cascade. Read
voice-pipeline-choice before going on.

## The sections

The spec has one section per review group, so `voice-agent-review` can score it item
by item. The full template, with the fields each section must fill, is in
[references/spec-template.md](references/spec-template.md).

| section | what it decides | skill to read |
| --- | --- | --- |
| callers and job | who calls, why, through which surface, and what success is | none |
| pipeline shape | the shape, the strings that must be exact, the voice, cost per minute | [voice-pipeline-choice](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-pipeline-choice/SKILL.md) |
| turn-taking | who decides the turn ended, and the endpointing delays | [voice-turn-taking](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-turn-taking/SKILL.md) |
| interruptions | what may be cut off, and what never is | [voice-interruptions](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-interruptions/SKILL.md) |
| latency budget | the per-stage targets and the run that will measure them | [voice-latency-budget](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-latency-budget/SKILL.md) |
| prompt | the blocks, the spoken-output rules, the confirmation wording | [voice-prompting](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-prompting/SKILL.md) |
| tools | every tool, whether it writes, its deadline, filler, and read-back | [voice-function-tools](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-function-tools/SKILL.md) |
| telephony | detection, transfers, digits, consent, dialing windows | [voice-telephony](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-telephony/SKILL.md) |
| evals | the scenarios, the assert and judge split, the release gate | [voice-agent-evals](https://github.com/mahimailabs/voice-ai-skills/blob/main/skills/voice-agent-evals/SKILL.md) |
| decisions log | each choice, what was rejected, and when to revisit it | none |

A surface the agent does not have is written as "not applicable" with one line of
reason. A web-only agent still writes the telephony section, and it says why.

## The loop

1. Ask. Work through the questions above until the callers-and-job and shape sections
   are filled.
2. Draft. Fill the template one section at a time. Show each section and wait for the
   person's yes or edits before the next. Save the spec as a file, for example
   `docs/designs/<agent>.md`.
3. Review. Run `voice-agent-review` on the spec file in fresh-reviewer mode. On a spec,
   an item passes when the spec commits to the value or behavior its pass condition
   names. Items that need a measured run pass when the spec names that run, and stay
   open until it exists.
4. Resolve. For each FAIL, change the spec, or record an accepted trade-off in the
   decisions log with its reason and revisit date. Re-review once. A second round of the
   same findings is a decision for the person, not another loop.
5. Approve. The person, not the agent, marks the spec approved. Code starts after that.

When the agent ships, review the code with `voice-agent-review` and compare it with the
spec. A difference is either a bug or a decision the log is missing.

## A decision that can be checked

Every number in the spec carries four things: the value, the range it may move in, the
symptom that would move it, and how it will be measured.

| weak | checkable |
| --- | --- |
| "fast responses" | p50 under 800 ms and p95 under 1400 ms end to end, measured over 50 turns on the phone path |
| "handle interruptions" | the booking read-back is uninterruptible; everything else stops after 2 words on the phone path |
| "confirm before booking" | read back name, date, and time in words, then ask "Shall I book that?" and call the write only after a yes |
| "good test coverage" | ten scenarios including identity, refusal, timeout, and voicemail, audio run nightly and before release |

## Using this skill

Read related skills by name from your installed skills when available. The repository
links are optional deeper guidance; this skill and its bundled template can be used on
their own. If a linked skill is unavailable, continue with the rules here and name any
section you could not complete. Without `voice-agent-review` installed, the spec can
still be written, but it has not been scored: say so at the top.

## The clinic agent spec

The clinic booking agent from the other skills, as its first two sections would read.

```markdown
## Callers and job
Patients call the clinic line to book, move, or cancel a routine appointment.
Inbound phone only. English. Success: a booked slot the patient confirmed, in under
three minutes, with no human transfer.

## Pipeline shape
Cascade. The caller must hear the date and time exactly, and speech-to-speech models
paraphrase them. Exact strings: the booking read-back and the confirmation question.
Voice pinned by ID in config. Cost per minute written in the decisions log, re-check
in 90 days.
```

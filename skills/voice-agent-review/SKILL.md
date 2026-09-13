---
name: voice-agent-review
description: Review a voice agent codebase or design against a 40-item checklist and produce a scored report covering pipeline choice, turn-taking, interruptions, latency, prompting, tools, telephony, and evals. Each failed item names the skill to read next. Use when someone asks to review my voice agent, asks whether a voice agent is production ready, before a launch, or when auditing an inherited voice agent codebase.
license: MIT
metadata:
  author: mahimairaja
  version: "0.1.0"
  category: voice-ai
---

# Voice Agent Review

This skill scores a voice agent against 40 checkable items and returns three fixes.
It decides whether the agent is ready for real callers, and what to repair first.

## Use this when

- Someone asks whether a voice agent is production ready.
- You inherited a voice agent codebase and need to know what is wrong first.
- A launch date exists and nobody has scored the agent against anything.
- Real calls are failing and you need the systemic cause, not one transcript.
- You are reviewing a design document before the code is written.

## Do not

- Do not review it like a web service. Uptime says nothing about turn taking.
- Do not score without reading the system prompt. That score is invalid.
- Do not pass an agent whose write tools fire with no read-back gate.
- Do not pass an agent with no audio tests. Text runs miss every timing failure.
- Do not score from the README. Read the config, the tools, and the prompt.
- Do not report a score without three concrete fixes, each naming a file.
- Do not raise a score because the team explains the gap in conversation.

## Read this before you score

1. The system prompt, in full. It carries wording, confirmation, and refusal rules.
2. The tool definitions: docstrings, arguments, timeouts, and which ones write.
3. The session or pipeline config: detector, endpointing delays, interruption knobs.
4. The eval suite: scenario count, the assert versus judge split, audio or text.

Read them in that order. The config explains what the prompt could not fix, and the
eval suite tells you which failures the team already knows about.

A score produced without reading the system prompt is invalid. Most failures in the
prompting, tools, and interruptions groups are visible only there. If the prompt is
not in the repository, stop and report "not scored" rather than a low score.

Score one deployed path, not a codebase. When a repository holds the same agent on two
stacks, pick the one that actually takes calls and name it in the header. Scoring the
union flatters the agent, because a gap covered on one stack is still a gap on the one
callers reach. If both ship, score both and file two reports.

## The eight groups

| group | what it scores | skill to read on failure |
| --- | --- | --- |
| pipeline choice | the shape, and whether exact wording survives it | [voice-pipeline-choice](../voice-pipeline-choice/SKILL.md) |
| turn-taking | who decides the caller has finished, and after how long | [voice-turn-taking](../voice-turn-taking/SKILL.md) |
| interruptions | what stops the agent, and what must never be stopped | [voice-interruptions](../voice-interruptions/SKILL.md) |
| latency | the five timings, measured on a real call | [voice-latency-budget](../voice-latency-budget/SKILL.md) |
| prompting | whether the prompt was written for the ear | [voice-prompting](../voice-prompting/SKILL.md) |
| tools | deadlines, fillers, read-backs, and what comes back | [voice-function-tools](../voice-function-tools/SKILL.md) |
| telephony | answering, transfers, digits, consent, narrowband | [voice-telephony](../voice-telephony/SKILL.md) |
| evals | what is asserted, what is judged, and what runs in CI | [voice-agent-evals](../voice-agent-evals/SKILL.md) |

Each group holds five items worth one point each. The 40 items, with a pass condition
for every one, are in [references/checklist.md](references/checklist.md).

## How to score

One point per item. Pass or fail, no half points, 40 total. An item you cannot check
from the code is a fail, not a skip. Record the missing evidence in the findings.

| score | band | what it means |
| --- | --- | --- |
| 0 to 19 | not ready | internal demo only. No real caller reaches it |
| 20 to 29 | pilot | real callers with a human fallback and a monitored queue |
| 30 to 35 | production candidate | ship after the three fixes and one more audio run |
| 36 to 40 | production | ship, and keep the audio suite on the release gate |

Every report ends with the three fixes to do first. A score with no fixes is a number
nobody can act on. The report format is in
[references/report-template.md](references/report-template.md).

## How to pick the three fixes

Rank by severity first. Call-breaking beats annoying, every time.

| rank | severity | example |
| --- | --- | --- |
| 1 | hard fail | a write tool fires with no read-back the caller confirmed |
| 2 | call-breaking | the agent cuts a date of birth in half and books the wrong patient |
| 3 | measurable | p50 at 1560 ms, so callers talk over the agent on every turn |
| 4 | annoying | the agent opens every answer with the same filler phrase |

Within a tie, the cheapest change wins. A config value beats a prompt rewrite, and a
prompt rewrite beats a pipeline change. If two hard fails tie, fix the one that lands
in a single commit first, because the second one needs a measurement run behind it.

Name the file and the line for each fix. A fix nobody can locate is a complaint.

## The four hard fails

| hard fail | how to check | why it caps the score |
| --- | --- | --- |
| no read-back gate on a write | a side-effecting tool is reachable with no confirmed read-back, or that read-back is interruptible | the agent books the wrong slot and the caller hears a confirmation for it |
| no audio tests | the suite runs in text only, or the audio run is not on the release gate | turn taking, barge-in, and pronunciation are untested |
| no latency measurement | the five per-turn timings are not logged, or only an average exists | you cannot fix what you cannot see, and the first fix is guessed |
| uncertain AMD treated as human on outbound | the outbound path branches uncertain into the human conversation | the agent asks a question into a recording and leaves dead air |

An agent carrying any of these cannot be scored above pilot, whatever the total is.
The cap only ever lowers a band. It never raises one, so an agent at 12 of 40 with a
hard fail stays at not ready. A hard fail on a surface the agent does not
have is marked not applicable, not failed. An inbound-only agent skips hard fail four
and fails the two outbound items in the telephony group. An agent with no phone path at
all scores the group zero.
Record it in the `Cap` field of the report header. At least one stack's
own guidance treats an uncertain result as human, so expect to find it in code that
followed the vendor example. The failure is asymmetric: a person hearing a short
self-contained line loses nothing, a machine hearing a question records silence.

## The clinic agent scored

The clinic booking agent as it was first written, before any of these skills were
applied to it. It is not the code in `examples/clinic-agent/`. That example already
makes the interruption, latency and tool choices these skills require, and it carries
no telephony and no eval suite at all, so it would fail a different set of items. This
table is here to show the shape of a report, not to score the repo.

| group | score | the gap that cost the points |
| --- | --- | --- |
| pipeline choice | 5 | none. Cascade, chosen because the read-back must be exact |
| turn-taking | 4 | max endpointing delay left at 5.0 s with no written reason |
| interruptions | 3 | min interruption words 0 on the phone path, and no resume after a false stop |
| latency | 2 | one average number, measured from a laptop over Wi-Fi |
| prompting | 4 | dates written as digits in two prompt examples |
| tools | 3 | `book_appointment` has no deadline, and returns raw JSON |
| telephony | 2 | uncertain result goes to the human path, no hold audio, recording unannounced |
| evals | 2 | nine scenarios, text only, no latency in the run |

Total 25 of 40. Band: pilot on the total, and held there by three hard fails: no latency
measurement, uncertain answering machine results treated as human, and no audio tests.
File and line are omitted below because this agent is not in the repository. A real
report carries both for every fix.
Fix 1: branch uncertain answering machine results into the message path, then wait.
One config change, one commit, and it stops the reminder calls failing silently.
Fix 2: log the five timings per turn, then report p50 and p95 over 50 phone turns.
Fix 3: add the audio suite to the release gate with the ten clinic scenarios.

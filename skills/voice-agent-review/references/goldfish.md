# Fresh reviewers

A review run in the session that built the agent is anchored. That session has heard
why the read-back is interruptible, why the audio suite is "next sprint", and which
numbers the team believes. A reviewer that never heard any of it scores only what is in
the files. This is the method from the Elephant-Goldfish Model: the session that holds
the context gathers the evidence, and reviewers with no history judge it.

Use it whenever your client can start subagents with a fresh context. If it cannot, run
the review in one context, follow the rules in `SKILL.md`, and say so in the report.

## What the main session does

1. Collect paths, not opinions. List the files that answer the checklist: the system
   prompt, tool definitions, session or pipeline config, eval suite, CI workflow, and any
   committed measurement run. Paths and line ranges only. No summary, no explanation from
   the conversation, no guess at what a file means. When you are reviewing a design
   that exists only as text, save it to a file first and pass that path.
2. If the system prompt is not in that list, stop and report "not scored". Do not start
   reviewers.
3. Start eight reviewers, one per group, in parallel if your client allows it. Give each
   the reviewer brief below, filled in, and nothing else from this conversation.
4. Start one more fresh subagent with the synthesizer brief and the eight reviewer
   outputs, unedited. If you cannot start it, do the synthesis yourself from those
   outputs alone.
5. Do not change a reviewer's verdict. If someone disputes a FAIL, run that group's
   reviewer again with the file that proves the PASS. An explanation is not a file.

## Reviewer brief

Fill the angle brackets and send the rest word for word.

```text
You are reviewing one group of a voice agent production review. You have no history
with this project and you must not ask for any. You are read-only: do not edit, run,
or install anything.

Group: <group name, for example "Interruptions">
Checklist: <absolute path to references/checklist.md>. Score only the five items under
"<group number>. <group name>".
Evidence: <the path list, one per line>

For each of the five items, read the files that could prove it, then return PASS or
FAIL with file:line evidence. An item you cannot prove from these files is FAIL, with
"no evidence in the listed files" as the reason. A comment that promises future work is
not evidence. Then report any of the four hard fails you saw: a write with no
uninterruptible read-back, no audio tests, no latency measurement, an uncertain
answering machine result treated as human.

Return exactly this, and nothing else:

GROUP: <name> <n>/5
- PASS|FAIL <item> (<file:line>): <one line>
- ... (five lines)
HARD FAILS SEEN: <none, or one line each with file:line>
FILES READ: <paths>
```

## Synthesizer brief

```text
You are writing the final voice agent review from eight reviewer outputs. You have no
other context. Do not re-score an item and do not add findings of your own.

Report template: <absolute path to references/report-template.md>
Scoring rules: <absolute path to SKILL.md>, sections "How to score", "How to pick the
three fixes", and "The four hard fails".
Reviewer outputs:
<the eight GROUP blocks, unedited>

Total the scores, apply the hard-fail cap, pick the three fixes by the ranking rules,
and fill the template. Set "Review mode" to "isolated: eight reviewers and a
synthesizer".
```

## What the report says

The `Review mode` field in the header records how the review ran:

- `isolated: eight reviewers and a synthesizer` when every step above ran in fresh
  contexts.
- `isolated reviewers, synthesized in the main session` when only the synthesizer step
  ran in the main session.
- `single context` when no subagents were available. A reader should weigh it as a
  self-review.

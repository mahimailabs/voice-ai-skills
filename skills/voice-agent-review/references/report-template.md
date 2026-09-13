# Voice agent review report template

The exact output format for a scored review. Copy the block, fill every field, and
delete nothing. An empty field is a finding.

```markdown
# Voice agent review: <agent name>

- Date: <YYYY-MM-DD>
- Reviewer: <name>
- Commit: <short sha>
- Surface reviewed: <inbound line, outbound campaign, or both>
- Cap: <none, or "pilot, capped by N hard fails">

## Score

| group | score | out of |
| --- | --- | --- |
| pipeline choice | <n> | 5 |
| turn-taking | <n> | 5 |
| interruptions | <n> | 5 |
| latency | <n> | 5 |
| prompting | <n> | 5 |
| tools | <n> | 5 |
| telephony | <n> | 5 |
| evals | <n> | 5 |
| total | <n> | 40 |

Band: <not ready | pilot | production candidate | production>

## Hard fails

| hard fail | present | evidence |
| --- | --- | --- |
| no read-back gate on a write | <yes/no> | <file:line, or "none found"> |
| no audio tests | <yes/no> | <file:line, or "none found"> |
| no latency measurement | <yes/no> | <file:line, or "none found"> |
| uncertain answering machine result treated as human | <yes/no> | <file:line, or "not applicable, inbound only"> |

Any yes caps the band at pilot, whatever the total.

## The three fixes to do first

1. <fix> (<file:line>). Severity: <hard fail | call-breaking | measurable | annoying>.
   Cost: <one config value | one prompt block | one code path | a pipeline change>.
2. <fix> (<file:line>). Severity: <...>. Cost: <...>.
3. <fix> (<file:line>). Severity: <...>. Cost: <...>.

## Findings by group

### Pipeline choice <n>/5
- FAIL <item name> (<file:line>): <what the code does>. Read voice-pipeline-choice.
- PASS <item name>: <the evidence, in one line>.

### Turn-taking <n>/5
- FAIL <item name> (<file:line>): <what the code does>. Read voice-turn-taking.

### Interruptions <n>/5
- FAIL <item name> (<file:line>): <what the code does>. Read voice-interruptions.

### Latency <n>/5
- FAIL <item name> (<file:line>): <what the code does>. Read voice-latency-budget.

### Prompting <n>/5
- FAIL <item name> (<file:line>): <what the code does>. Read voice-prompting.

### Tools <n>/5
- FAIL <item name> (<file:line>): <what the code does>. Read voice-function-tools.

### Telephony <n>/5
- FAIL <item name> (<file:line>): <what the code does>. Read voice-telephony.

### Evals <n>/5
- FAIL <item name> (<file:line>): <what the code does>. Read voice-agent-evals.

## Not scored

- <item name>: <why the code could not answer it>. Counted as a fail.
```

Rules for filling it in. One line per finding. Name the file and the line for every
fail. Passes need one line of evidence, not a paragraph. Keep the three fixes ranked
by severity, and break a tie with the cheaper change. Do not add a group, and do not
drop a group that scored 5 out of 5: a reader needs to see what was checked.

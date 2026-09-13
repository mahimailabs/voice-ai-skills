# AGENTS.md

These skills carry engineering judgment, not API facts. Read them for the decision
and the number, never for a method signature.

1. Verify every SDK call against the vendor's own docs or docs MCP before writing it.
   The `## Adapters` sections are pinned to a version and a date, and they drift.
   Where a skill says "verify against current docs", that is an instruction.
2. `examples/clinic-agent/` is the worked example for six of the eight review groups. It
   carries no telephony and no eval suite on purpose. The same clinic agent is in every skill.
3. `skills/voice-agent-review/` is the entry point when you are asked to review,
   audit, or production-check a voice agent. It scores and routes to eight of the other
   nine; voice-full-duplex is reached through voice-pipeline-choice.
4. Start from the `## Do not` list. It is where a coding agent's default behavior is
   wrong for voice, and it is the highest-value part of every file.
5. Numbers here are defaults with a stated range and a symptom. Change one against a
   measurement, never against a preference.
6. The vendor-neutral core is what survives a port between stacks. The adapters do not.
7. `python scripts/validate.py` must pass before any change under `skills/` lands.

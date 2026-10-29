# Changelog

All notable changes to this collection are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Adapter claims are pinned to a stack version and a verification date. When a refresh
changes a claim, the entry names the skill and the stack.

## [Unreleased]

### Added

- Codex plugin install instructions. Codex installs `voice-ai@voice-ai-skills` from the
  existing marketplace file.
- `scripts/validate.py` rejects a `SKILL.md` body over 24,000 bytes, the Antigravity
  load limit.
- CI runs the validator and unit tests on Windows, and `.gitattributes` keeps LF line
  endings on every checkout.
- Dependabot for GitHub Actions and the site's npm packages.
- Behavioral scenarios for every skill in `tests/scenarios/`: a prompt, required and
  forbidden answer patterns drawn from the `## Do not` lists, criteria for a human
  reviewer, and passing and failing examples that CI uses to prove the patterns.
- `scripts/test_agent.py --trace claude|codex` parses the client's native trace. A
  case passes only when the expected skill was opened with a non-error result and the
  answer meets its patterns. The five old acceptance cases moved into the scenarios.

- `docs/neutrality.md`: vendor neutrality rules for the core, required adapter fields,
  criteria for adding a stack, refresh cadence, and conflict-of-interest disclosure.
- `CHANGELOG.md`.
- `CONTRIBUTING.md`: how to refresh an adapter, what is accepted and closed, and the
  checks to run before a pull request.
- Issue forms for adapter corrections, default challenges, new stacks, and tooling bugs;
  a pull request template; `CODEOWNERS`.
- `CODE_OF_CONDUCT.md`: Contributor Covenant 2.1.
- `site/`: the skills.mahimai.ca website, built with Astro Starlight. Every skill page, the
  combined “Do not” page, and the neutrality policy are generated from the repository on
  each build, and CI builds it on every pull request.
- skills.mahimai.ca home page: an authored page in the mahimai.ca chapter layout, with a
  real `voice-agent-review` run on the clinic example as its centerpiece, one-line copyable
  install commands, and the skills grouped by the part of the call they govern. The full
  report is published at `/example-review/`.
- skills.mahimai.ca visuals: the review score drawn as bars, the turn-taking clinic case as
  an animated timeline, the latency calculator's example as a budget chart, and the skills
  as a map of one call. Built with anime.js and Radix primitives, including a segmented
  light, dark, and auto theme toggle.

- `voice-agent-review` runs with fresh reviewers by default when the client can start
  subagents: eight read-only reviewers, one per group, see only file paths and the
  checklist, and a ninth writes the report from their outputs. Briefs are in
  `references/goldfish.md`, and the report header records the `Review mode`.
- A stamp line under each adapter heading records the package, pin, and verification
  date. `scripts/adapter_drift.py` and a weekly workflow report how far each pin is
  behind PyPI and open refresh issues for due adapters. Drift never fails a build.

- `voice-agent-spec`: writes a voice agent's design before code, one section per review
  group, asks the questions that decide the shape first, and has the spec scored by
  `voice-agent-review` with fresh reviewers. Template in `references/spec-template.md`.

### Changed

- GitHub Actions are pinned to commit SHAs, workflows default to read-only
  `contents` permission, and checkouts do not persist credentials.
- `python-dotenv` is pinned in the SDK contract job.

## [0.1.0] - 2026-09-16

First public collection.

### Added

- Ten skills in the Agent Skills format: `voice-agent-review`, `voice-agent-evals`,
  `voice-full-duplex`, `voice-function-tools`, `voice-interruptions`,
  `voice-latency-budget`, `voice-pipeline-choice`, `voice-prompting`,
  `voice-telephony`, and `voice-turn-taking`.
- Adapters for LiveKit Agents, Pipecat, and Vapi, each pinned to a version and a
  verification date.
- `voice-agent-review`: a 40-item checklist across eight groups and a report template.
- Latency budget calculator, bundled inside `voice-latency-budget/scripts/`.
- Clinic booking example on LiveKit and Pipecat, with shared confirmation state, tool
  deadlines, filler, and timeout reconciliation.
- Claude Code plugin marketplace entry.
- Validation: `scripts/validate.py`, regression tests, the `skills-ref` reference
  validator, and installer checks in copy and symlink modes in CI.
- Compatibility, testing, and SDK verification docs.


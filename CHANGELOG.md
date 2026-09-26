# Changelog

All notable changes to this collection are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Adapter claims are pinned to a stack version and a verification date. When a refresh
changes a claim, the entry names the skill and the stack.

## [Unreleased]

### Added

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


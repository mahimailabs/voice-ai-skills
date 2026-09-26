# Contributing

Thank you for helping. This collection is engineering judgment for coding agents that
build voice agents. A contribution is valuable when it makes a rule more correct, a
number better sourced, or an adapter more current.

Read these first:

- [`AGENTS.md`](AGENTS.md): how the skills are meant to be read and changed.
- [`docs/neutrality.md`](docs/neutrality.md): the rules for the vendor-neutral core and
  for every adapter.
- The [Q4 2026 roadmap](https://github.com/mahimailabs/voice-ai-skills/issues/1).

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Good first contributions

Look for issues labelled
[`good first issue`](https://github.com/mahimailabs/voice-ai-skills/labels/good%20first%20issue).
Most are adapter refreshes: one skill, one stack, checked against the vendor's current
docs. They need care, not deep voice expertise.

### Refreshing an adapter

1. Open the skill's `references/adapters.md` and its `## Adapters` section in `SKILL.md`.
2. Check every claim for that stack against the vendor's official docs, API schema, or
   source code. Never against a blog post or another summary.
3. Fix what changed. Keep one source link per claim.
4. Update the pinned version and the verification date, even if nothing else changed.
5. If a setting no longer exists, say so and say what to do instead. Do not delete the row.
6. Note changed claims in `CHANGELOG.md` under `Unreleased`.

## What we accept

- Corrections to adapter claims, with the source that shows the current behavior.
- Challenges to a default, with a measurement: what you measured, on which stack, and
  the symptom you saw. See [Challenge a default](.github/ISSUE_TEMPLATE/default-challenge.yml).
- New stacks that meet the criteria in [`docs/neutrality.md`](docs/neutrality.md#adding-a-stack).
  Open an issue before the pull request.
- New skills on the roadmap. Open or comment on the issue first.

## What we close

- Rewording without a change in meaning, including style-only edits to `## Do not` lists.
- Numbers without a source or a measurement.
- Claims copied from secondary sources.
- Anything that ranks, recommends, or favors a provider.
- Changes produced by a tool or model and submitted without the author checking every
  claim. Using a coding agent is fine; submitting what it wrote unchecked is not.

## Before you open a pull request

```sh
python scripts/validate.py
python -m unittest discover -s tests -v
python -m compileall -q examples/clinic-agent scripts
```

`validate.py` must pass for any change under `skills/`. Every skill must still work when
installed on its own, so links must stay inside the skill's folder or be full URLs.
See [testing](docs/testing.md) for installer, SDK, and coding-agent checks.

## Style

- Short declarative sentences. Say the decision, the number, the range, and the symptom.
- Start from the reader's failure, not the feature.
- Every number in the core has a range and a symptom, or a source.
- Adapter claims name a version and a date.

## Disclosure

If you work for, contract for, or are paid by a vendor, say so in any pull request that
touches that vendor's adapter or a core claim that names it. See
[`docs/neutrality.md`](docs/neutrality.md#money-and-conflicts-of-interest).

## Licence

By contributing you agree that your contribution is licensed under the
[MIT License](LICENSE).

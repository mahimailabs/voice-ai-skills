# Vendor neutrality and adapter policy

These skills carry engineering judgment that must survive a port between stacks. This
page sets the rules that keep them that way, for contributors and for vendors.

## The core

The core is everything in a `SKILL.md` above `## Adapters`, and every reference file
that is not an adapter file.

1. The core never recommends a provider, a model, or a stack. It states the decision,
   the default, the range, and the symptom.
2. The core may name a product only to describe a documented behavior or a measured
   number, and only with a source. Naming is not endorsement.
3. A default in the core must hold on every supported stack. If it holds on one stack
   only, it belongs in that stack's adapter.
4. Where stacks differ in capability, the core says what the capability does and what
   breaks without it. It does not say which stack has it.

## Adapters

An adapter maps the core's settings onto one stack. Adapters are symmetric: every stack
gets the same fields and the same scrutiny.

### Required fields

Every adapter section, in `SKILL.md` and in `references/adapters.md`, carries:

| field | example |
| --- | --- |
| stack name as the heading | `### Pipecat` |
| pinned version, or the docs state | `Pinned to LiveKit Agents for Python 1.8.x` or `Unversioned docs` |
| verification date | `verified 11 September 2026` |
| mapping table from this skill's settings to the stack's | `\| this skill \| Vapi \|` |
| one source link per claim | official docs, API schema, or source code |
| traps, marked `TRAP:` | a setting that is silently ignored |

A setting the stack does not offer is written as not available, with what to do
instead. It is never left out: a missing row reads as an oversight, not a gap.

### Order and wording

- Adapters appear in alphabetical order by stack name. Order carries no meaning.
- Adapters describe; they do not compare. No "better", "faster", or "recommended" across
  stacks. A measured number is allowed with its source, conditions, and date.
- No rankings, leaderboards, or scores of vendors anywhere in the collection.

## Adding a stack

Open an issue before the pull request. A new stack is accepted when:

1. It is publicly documented, or its source is public, so every claim can be checked.
2. It maps onto at least the settings of `voice-turn-taking`, `voice-interruptions`,
   and `voice-function-tools`.
3. Someone commits to the first refresh after the initial pull request.

Vendors are welcome to propose or correct their own adapter. Their pull requests meet
the same rules and the same review as anyone else's.

## Keeping adapters current

- Re-verify an adapter when its stack ships a minor or major release, and at least every
  90 days.
- Re-verification updates the version and the date, even when nothing else changes.
- An adapter not verified for 180 days is marked stale at the top of its section.
- A stale adapter with nobody to refresh it is removed in the next minor release, and
  the removal is recorded in `CHANGELOG.md`.

## Money and conflicts of interest

- No vendor can pay for inclusion, order, wording, or removal of an adapter.
- Sponsorship of the project buys no influence over content. A sponsor that is a vendor
  is listed as such.
- A contributor employed by, contracting for, or paid by a vendor says so in any pull
  request that touches that vendor's adapter or a core claim that names it.
- The maintainers build voice agents for clients on more than one stack. That work
  informs the defaults; it does not decide which stacks are supported.

## Enforcement

A pull request that breaks these rules is changed or closed, whoever opens it. If you
think an adapter or a core claim favors a provider, open an issue with the file and the
line.

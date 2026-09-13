# Validated gap resolution

Changes made after the September 13, 2026 portability/example audit. This is a local
implementation record; the changes reach remote installations only after publication.

| Validated gap | Resolution | Evidence |
| --- | --- | --- |
| Installed latency helper missing | Canonical script bundled inside its skill; root command forwards to it | Isolated copy tests and real installer runs |
| Selective installs lose sibling links | Self-contained references; optional repository links and explicit missing-skill fallback | All ten skills individually validated after installation |
| Source-only validation | Recursive link containment, required reference validator, copy/symlink installer CI, SDK regression CI | Repository tests and installer checks pass; native acceptance cases added |
| No protected pre-write read-back | Shared two-phase confirmation state; adapter playback receipts; Pipecat microphone/input gating | Ordering, interrupted playback, cancellation, correction, and duplicate tests |
| Misleading five-timing claim | Native LiveKit role-specific fields; Pipecat estimates; null for missing; snapshot-aware p50/p95 report | Metric callback and aggregation tests; real-call measurement remains unverified |
| Missing fillers | All backend operations share a delayed interruptible filler | Slow-read timeout tests |
| Missing slot identifiers | Silent IDs retained alongside spoken descriptions | Lookup → availability → booking tests |
| Timeout reported as “nothing booked” | Mark uncertain before write, reconcile by key, never blindly repeat | Commit-then-timeout and unresolved-timeout regressions |
| Unhandled Pipecat read timeout | Shared authored errors and safe adapter result callbacks | Deadline and SDK callback tests |
| Example documentation overclaims | Shared prompt, actual capability mapping, explicit example limits | Example README and review-skill wording corrected |
| Missing environment/offline guidance | Python requirement and docs-unavailable policy shipped in skills | Metadata validation and compatibility docs |

The README now leads with agent-neutral installation, links the compatibility matrix,
and uses the supplied light/dark covers. Claude's plugin remains an optional install path.

**Still unverified:** native model discovery/instruction-following in each coding
agent, live speech providers, real transport playback, and PSTN calls. The native
acceptance runner and criteria are ready, but no synthetic output is reported as a
native-client pass. Telephony, persistence, authentication, and a voice eval suite
remain intentional omissions from the clinic example.

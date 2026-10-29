# E15-B: Does the historical figure reproduce on the author's repositories as they were on 2026-07-27?

Status: **REGISTERED, NOT RUN.** This file is committed alone, before any script exists, before any July commit has been resolved, and before any repository has been scanned at a July commit.
Registered 2026-10-29.

## Why

E15 v2 ([RESULTS.md](../E15/run/RESULTS.md)) found the author's repositories at a median of 11.0 verification-shaped files (mean 15.9: 333 files over 21 repositories), against 3.0 in both sampled arms. The historical observation that motivated E15 was the opposite: 1.2 per repository for the author against 34.7 for popular CI libraries.

E15's own Limitation 1 says it cannot tell two explanations apart:

- **(R) The repositories changed.** The July figure was roughly right, and verification code was added since. `sovereign-veritas`, `vacuity_lint.py` and `principia-artificialis` are E15's top three.
- **(N) The figure does not reproduce.** Today's instrument does not give a figure near 1.2 even on July's code, so the historical number reflects the instrument or the definition it used, not the repositories.

E15-B scans the same population at its July commits with E15 v2's instruments. It asks only which explanation the data supports. It does not ask whether the historical figure was computed correctly; that instrument no longer exists.

## What the historical record says (checked against its source before writing this)

Source: `research_notes/note052_verification_that_cannot_fail.md` in `holland202/principia-artificialis`, "Registered predictions and results".

- **1.2** verification-shaped files per repository, from `vacuity_scan.py`, a clean-room reimplementation run in a sandbox on **2026-07-27** and never committed. The note does not name the repositories in that arm.
- **26** verification-shaped entry points across **12** repositories (about 2.2 per repository), from `vacuity_lint.py` itself, run on the author's device the same day.

Both are history. Neither is a registered expected value.

## Population and checkout (mechanical; no new selection event)

- **Population:** every repository in E15 v2's committed Arm A listing, `E15/selection/run/arm_a.json` (retrieved 2026-10-28, eligible or not), whose `fork` field is false. Forks are excluded because a fork's code is not the author's; note052's own later registration excludes forks for the same reason. Any fork that would otherwise qualify is listed by name.
- **Cutoff:** `2026-07-27T23:59:59Z`.
- **July commit:** the result of `git rev-list -1 --first-parent --before=2026-07-27T23:59:59Z <default branch>` on a full-history clone. That is the newest first-parent commit with a committer date at or before the cutoff.
- **Arm J:** each population repository that has a July commit and passes E15's eligibility rules 1–2 *at that commit*: at least 5 and no more than 2000 `*.py` files.
- A repository whose clone fails, or whose July commit cannot be checked out, is recorded as UNAVAILABLE and counted. It is not replaced.
- Repositories that were public in July but are private or deleted now cannot be measured. That is a limitation of the design, stated here, not corrected.

## Instruments and exclusions (unchanged from E15 v2)

- **Primary:** `vacuity_lint.py` from `b0db5ac3fc2b20eb16abb6594f1e19746be62650`, sha256 `a92963c69fa129dbccf94e9672419c2dd2768950d97318183bc8b2820ee815d4`.
- **Secondary**, sensitivity only: `vacuity_lint.py` from `e549dbfe9d8c0a03399bef45b66edf7bb6552f58`, sha256 `7a5b8d100457128f5cd17c418ea28af480e8c8a488968211508b08b09997292c`.
- **Exclusions:** E15 v2's list, applied by deleting the paths before any scan: `conftest.py`; `examples/`, `example/`; `.venv/`, `site-packages/`, `node_modules/`, `third_party/`.
- Both instruments' sha256 values are checked before the first scan, before every repository and after the last.
- A scanner traceback, or an exit code outside 0, 1 and 2, VOIDS the run. Neither scanner is modified during E15-B.

## Gates (decide whether the run can carry a verdict)

- **G0, pipeline reproduces E15.** E15-B's pipeline is also run on every Arm J repository at its **E15 v2 recorded commit**. It must reproduce E15 v2's recorded primary `verification_shaped` exactly for each one. One mismatch VOIDS the run. This also shows the pipeline can return high counts (E15 recorded values up to 83).
- **G1, cutoff resolved correctly.** For every July commit: its committer date is at or before the cutoff, and its first-parent child, if it has one, is after the cutoff. One failure VOIDS the run.

## Primary outcome

**M_J:** the mean primary-instrument `verification_shaped` count per repository over Arm J. A mean, because the historical 1.2 was a mean (15 over 12). The median and the full sorted distribution are also reported.

## Classification (fixed now; the bands contain both historical figures)

| M_J | Verdict | Reading |
|---|---|---|
| ≤ 2.4 | **REPRODUCES** | The July figure was roughly right. E15's reversal is explained by the repositories changing (R). |
| ≥ 4.8 | **DOES NOT REPRODUCE** | Today's instrument does not give the July figure even on July code (N). The reversal is not only the repositories changing. |
| between | **INCONCLUSIVE** | Neither reading is supported. |

The bands are a factor of 2 and a factor of 4 above 1.2. Exact agreement is not expected, because the historical instrument differed from the pinned one. The REPRODUCES band contains both historical figures, 1.2 and about 2.2.

## Predictions (Claude's, registered before any data)

- **P1.** M_J is in the REPRODUCES band. Basis: note052's device figure of about 2.2 per repository with `vacuity_lint.py` itself, and E15 Limitation 1's observation that the three largest Arm A repositories gained verification code after July. Confidence: low.
- **P2.** Over repositories in Arm J that also have an E15 v2 count, more increased from July to E15 than decreased. **CONFIRMED** only if increases outnumber decreases and the exact two-sided sign test (ties dropped) gives p < 0.05. Otherwise **NOT CONFIRMED**.

## Descriptive, no verdict

- Number of Arm J repositories, against the historical 12. Names of UNAVAILABLE, ineligible and fork repositories.
- Total `.py` files scanned at July commits. No historical total is published, so none is compared.
- Per-repository table: July commit, July count, E15 commit, E15 count, difference.
- Secondary-instrument counts and the per-repository difference between instruments.

## What E15-B can and cannot say

- **Can:** whether E15 v2's instruments give a figure near the historical one on the author's repositories as they were on 2026-07-27.
- **Cannot:**
  - whether the historical 1.2 was computed correctly (its instrument and repository list were never published);
  - anything about repositories that are no longer public;
  - anything about authorship. E15-B has one arm and no comparison group.
- **Self-tested.** Run in Claude's workspace, not independently reproduced.

## Pre-mortem

- **History rewritten since July** (force-push, delete and recreate): the July commit is missing and the repository is counted UNAVAILABLE. If that removes most of the population, the result is reported as a shortfall.
- **Commits made on 2026-07-27 after the historical scan** are included by the cutoff. The scan's time of day is not recorded. This can only raise M_J slightly, which would move a borderline result away from REPRODUCES, not toward it.
- **Committer dates can differ from push dates.** A commit made before the cutoff but pushed later counts as July. Stated, not corrected.
- **Arm J differs from the historical arm** (repositories since made private, or created that day). The count and the names are reported. A reader can judge the overlap.

## Communication

Nothing is sent to anyone about E15-B. The owner decides after results exist.

## Provenance

Drafted by Claude (Anthropic, Claude Opus 5.5) on 2026-10-29 at Chad Holland's direction. No July commit was resolved and nothing was scanned. Not reviewed line by line by Chad.

# E15-B results: the historical figure does not reproduce on July's code, by a hair

Status: **EXECUTED, SELF-TESTED.** Run 2026-10-29 in Claude's workspace. Not independently reproduced.
- Registration: [PREREG.md](../PREREG.md) (`2006ee7`) and [PREREG_ADDENDUM_A4.md](../PREREG_ADDENDUM_A4.md) (`9e03579`).
- Pre-scan decisions: [README.md](README.md), committed with the script at `b2553a9` before any July commit was resolved.
- Raw records: `output/` (`af3d143`).

## What could have gone wrong, first

- **The verdict sits on a knife edge.** M_J is 4.8571 against a registered line of 4.8. One verification-shaped file fewer in any one of the seven repositories gives 4.7143, which is INCONCLUSIVE. The registration fixed the bands without asking how close a result could land to one. The verdict is reported as registered, and its fragility is stated rather than resolved.
- **P2 could never have been confirmed.** With 5 non-tied pairs, the smallest possible two-sided sign-test p is 0.0625, so P2 failed for lack of data, not because of the direction. The registration printed no feasibility count. The size of Arm J was knowable from repository creation dates without scanning anything, and was not checked.
- **P1, Claude's own prediction, is refuted.**
- **Arm J is not the historical arm.**
  - It has 7 repositories, not 12. Six repositories that had July commits held fewer than 5 `.py` files and fail E15's eligibility rule 1. The historical scans included every repository, whatever its size.
  - Arm J also contains `quasar-v2`, which was private in July: its README at the July commit (`b089ac8`) begins "QUASAR v0.2 (private)". A public-repository arm then could not have included it.
  - The registration drew its population from today's public listing, so it could see neither difference. Both are recorded here, not corrected.
- **A small registration slip.** The first registration commit (`2006ee7`) carried one line of `RESEARCH_INDEX.md` with PREREG.md, rather than PREREG.md alone.
- **Reviews that have not happened:** independent reproduction, and line-by-line review by the owner.

## Outcomes (pasted from `output_console.log`)

```
STATUS COMPLETE
ARM J n=7 mean=4.8571 median=5 values=[2, 4, 5, 5, 6, 6, 6]
CLASSIFICATION DOES NOT REPRODUCE (REPRODUCES <= 2.4, DOES NOT REPRODUCE >= 4.8)
P1 REFUTED: registered REPRODUCES
P2 NOT CONFIRMED: increases 5, decreases 0, ties 2, sign-test p=0.0625
DIGEST 4ecac6843cd1263d38e9eee308550fa2a57bc90bc4b55bfe14bb485a24f45d77
RECORDED not pinned yet: exit 0
exit=0
```

**Gates:** G0 matched E15 v2's recorded count on all 7 Arm J repositories. G1 held on all 13 July commits. 0 repositories were UNAVAILABLE.

| | Registered | Result | Verdict |
|---|---|---|---|
| Classification | M_J ≤ 2.4 REPRODUCES; ≥ 4.8 DOES NOT REPRODUCE | M_J = 4.8571 | **DOES NOT REPRODUCE** (by 0.057) |
| P1 | REPRODUCES | DOES NOT REPRODUCE | **REFUTED** |
| P2 | more increases than decreases, sign test p < 0.05 | 5 up, 0 down, 2 ties, p = 0.0625 | **NOT CONFIRMED** (could not have been confirmed at this n) |

Under PREREG.md's reading, DOES NOT REPRODUCE means: today's instrument does not give the July figure even on July's code, and E15's reversal is not only the repositories changing.

## Per repository

Arm J (eligible at the July commit):

| Repository | July commit | July count | Secondary | E15 commit | E15 count | Change |
|---|---|---|---|---|---|---|
| `principia-artificialis` | `c911fff` (2026-07-27) | 6 | 6 | `78726b8` | 36 | +30 |
| `quasar` | `6698535` (2026-07-26) | 5 | 5 | `ba050b6` | 18 | +13 |
| `quasar-v2` | `b089ac8` (2026-07-13) | 6 | 6 | `fc59f1e` | 7 | +1 |
| `skn-v1-` | `1e22c48` (2026-07-23) | 2 | 2 | `ce7bd97` | 2 | +0 |
| `slc-v12-` | `14c8e63` (2026-07-27) | 5 | 5 | `311bcae` | 15 | +10 |
| `sovereign-evolution` | `fef663c` (2026-07-12) | 4 | 5 | `f0233c0` | 11 | +7 |
| `sovereign-suite` | `a1c990d` (2026-07-27) | 6 | 6 | `56ca9c3` | 6 | +0 |

- **Ineligible at the July commit** (fewer than 5 `.py` files): `coverage-preserving-synthesis` (1), `edge-ai-primitives` (4), `polytope-explorer` (2), `qolas-synthesis` (1), `qsleuth` (4), `sentinel-batadal-validation` (1).
- **No commit at or before the cutoff** (13): `eace`, `eunoia`, `evidence-ledger`, `holland202`, `sentinel-hai-validation`, `sovereign-veritas`, `token-veritas`, `vacuity_lint.py`, `veritas-companion`, `veritas-eval-harness`, `veritas-holo`, `veritas-origin`, `veritas-science`.
- **Fork excluded:** `aap-conformance`.
- **Secondary instrument** (`e549dbf`): mean 5.0, the same classification. It differs from the primary on one repository, by 1 (`sovereign-evolution`). 154 `.py` files were scanned at the July commits.

## Post hoc: not registered, written after the results were seen, no verdict

`posthoc/small_repos.py` scans the six ineligible repositories at their July commits with the same primary instrument and exclusions. Output, pasted from `posthoc/small_repos_console.log`:

```
POST HOC: all 13 repositories with a July commit: mean 2.8462, total 37
```

The six small repositories hold 3 verification-shaped files between them (`edge-ai-primitives` 1, `polytope-explorer` 2, the rest 0). Dropping `quasar-v2`, which was private in July, leaves 12 repositories and 31 files, a mean of 2.5833.

| Figure | Per repository |
|---|---|
| Historical, clean-room scanner (note052) | 1.2 |
| Historical, `vacuity_lint.py` on the owner's device (note052: 26 entry points across 12 repositories) | about 2.2 |
| July, registered (Arm J, rule 1 applied) | 4.8571 |
| July, post hoc, every repository with a July commit | 2.8462 |
| July, post hoc, without `quasar-v2` | 2.5833 |

Read as exploration only:
- No variant reaches 1.2.
- Dropping the eligibility rule moves the July figure most of the way toward the device figure, but not into the REPRODUCES band (2.5833 > 2.4).
- Most of the registered gap between 4.86 and the historical figures looks like a difference in which repositories are counted, not a difference in the code. A new registration would have to test that.

## What this shows, and what it does not

- **Design (C-DESIGN):** an observational re-measurement, so every claim here is descriptive.
- **Shows:** with E15 v2's pinned instrument and eligibility rule, the author's repositories as they were on 2026-07-27 average 4.86 verification-shaped files. That is about four times the historical 1.2.
- **Shows:** growth since July is large. 13 of today's 26 non-fork repositories had no commit by the cutoff. Of the 7 compared, 5 gained verification-shaped files and none lost any. Principia went from 6 to 36, and E15's top three (`sovereign-veritas` 83, `vacuity_lint.py` 54, Principia 36) are all either new since July or grew by 30.
- **Together:** both of PREREG.md's readings contribute. E15's headline gap (a median of 11 against 3 and 3) is mostly the estate growing since July. The July figure itself is not reproduced by today's instrument and rule, and the post hoc numbers point at the rule and at which repositories are counted.
- **Does not show:** whether the historical 1.2 was computed correctly, since its instrument and repository list were never published. Nothing about authorship. Nothing about repositories that are private now.

## Still open

- A registered follow-up without eligibility rule 1, whose feasibility count and test power are fixed before any scan.
- Independent reproduction. E15's `REPRODUCE.md` pattern would carry over: the population, July commits and pinned instruments are all public.

## Provenance

Run and written up by Claude (Anthropic, Claude Opus 5.5), 2026-10-29, after the owner delegated the session's path to Claude. Every number above is pasted from `output_console.log`, `posthoc/small_repos_console.log` or `output/scans.json`. Not reviewed line by line by Chad.

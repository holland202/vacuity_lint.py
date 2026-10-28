# E15 v2 results: the historical gap does not reproduce, and runs the other way

Status: **EXECUTED, SELF-TESTED.** The author's procedure was run by Claude in Claude's cloud workspace. Not independently reproduced. Registration: [PREREG_v2.md](../PREREG_v2.md). Pre-scan decisions: [README.md](README.md), committed at `849af6a` before any scan. Selection: [../selection/](../selection/), audited 16/16.

## Verdicts (primary instrument, pasted from `output_console.log`)

```
{"P1_C_gt_B": "NOT CONFIRMED", "P2_A_lt_C": "NOT CONFIRMED", "P3_A_equiv_B": "INCONCLUSIVE", "P4_control": "PASS"}
```

| Prediction | Registered claim | Result | Verdict |
|---|---|---|---|
| P1 | Arm C median > Arm B median | median diff C−B = 0.0, 95% CI [-2.5, 5.5], Mann-Whitney p = 0.6321 | **NOT CONFIRMED** |
| P2 | Arm A median < Arm C median | median diff A−C = **+8.0** (wrong direction), 95% CI [-1.0, 13.0], p = 0.0529 | **NOT CONFIRMED** |
| P3 | A ≈ B within ±2.0 | median diff A−B = **+8.0**, 95% CI [1.5, 13.0] | **INCONCLUSIVE** |
| P4 | anti-vacuity: C vs itself, rate in [0.02, 0.08] | 1000 distinct splits, rate 0.046 | **PASS** |

P4 passed, so the comparisons are not void.

## What failed, first

- **P2 failed in direction, not only in significance.** It predicted the author's repositories have fewer verification-shaped files than CI repositories. Their median is 8 files *higher*. The p-value (0.0529) misses the registered 0.05 line, so no difference is claimed, but there is no support for the predicted direction.
- **P1 failed.** Repositories with a CI config path did not have more verification-shaped files than those without. Both medians are 3.0.
- **P3, the load-bearing prediction, is INCONCLUSIVE.** It was built to tell "A is similar to B" apart from "A is far below B". The interval [1.5, 13.0] is neither inside ±2 nor below −2. It sits mostly *above* B. The registration did not anticipate A being higher, so it has no verdict for that case. The rule's own answer is INCONCLUSIVE, and that is what is reported.

## Primary outcome: verification-shaped files per repository

| Arm | n | median (primary) | IQR (primary) | median (secondary `e549dbf`) | IQR (secondary) |
|---|---|---|---|---|---|
| A | 21 | 11.0 | 5.0–16.0 | 11.0 | 5.0–16.0 |
| B | 30 | 3.0 | 1.0–7.0 | 3.0 | 1.0–7.0 |
| C | 20 | 3.0 | 1.0–9.0 | 3.0 | 1.0–8.75 |

Full sorted distributions are in `output/results.json` (`values_sorted`). Per-repository counts are in `output/scans.json`. Unavailable commits: A 0, B 0, C 0. Repositories with coverage errors: 0 in every arm.

**The plain reading.** The historical observation behind E15 was 1.2 verification-shaped files per repository for the author against 34.7 for popular CI libraries. Under this registered, reproducible procedure the order flips: the author's repositories have median 11.0, and both sampled strata 3.0. Because P1–P3 did not reach their registered verdicts, this is a description, not a confirmed difference.

## Secondary outcome: repositories with at least one finding (underpowered, as registered)

| Arm | k/n | proportion | 95% Clopper-Pearson |
|---|---|---|---|
| A | 9/21 | 0.429 | [0.218, 0.660] |
| B | 14/30 | 0.467 | [0.283, 0.657] |
| C | 5/20 | 0.250 | [0.087, 0.491] |

All three intervals overlap widely. No conclusion is drawn.

## Instrument sensitivity (descriptive; run in deviation from the registered parser timing)

The original scanner `e549dbf` gives the same four verdicts: P1 NOT CONFIRMED, P2 NOT CONFIRMED, P3 INCONCLUSIVE, P4 PASS. Medians are identical, and only C's upper quartile moves (9.0 → 8.75). 20 of 71 repositories differ by 1–4 files between scanners. The choice of instrument did not change any verdict.

## Other registered descriptive counts

- **Kind C (`bench` paths):** verification-shaped files under paths containing `bench`: A 1, B 1, C 23. 21 of C's 23 come from one repository (LexiLingo, 334 verification-shaped files, the largest in the study). This inflates C's upper tail, not its median.
- **Exclusions removed** 54 `.py` files across all arms before scanning.

## Limitations that bear directly on this result

1. **Arm A is measured today, not in July.** The historical 1.2 figure came from the author's repositories as they were then. Since then, verification code has been added to them deliberately: `sovereign-veritas` (83), `vacuity_lint.py` (54) and `principia-artificialis` (36) are Arm A's top three. E15 measures the repositories as they are. It cannot say whether the July figure was wrong or the repositories changed.
2. **The instrument was developed against Arm A** (PREREG_v2 limitation 1). Tuning that removed false positives from the author's code plausibly lowers A, so it does not explain A being higher, but the asymmetry stands.
3. **The pool is effectively 50-star repositories** ([selection audit](../selection/AUDIT.md)). B and C describe the top of the 5..50 band, not the whole band.
4. **Arm A includes 1 fork and 2 archived repositories** that the pool query excludes, per the registered wording.
5. **Verification-shaped files are a surface measure.** They count files that look like checks, not whether those checks are any good. Type B vacuity is not measured at all.
6. **Authorship is not measured.** Nothing here supports any claim about AI-assisted code.

## Left unrun

- Whether CI or code review is the operative variable (registered as unrun).
- VL-FP-003's R6 can now be run on this committed selection as a secondary look at data already drawn.
- A dated re-measurement of Arm A from its July commits would separate "the July figure was wrong" from "the repositories changed". This is not registered.

## Provenance

Scan, analysis and this write-up by Claude (Anthropic, Claude Opus 5.5), 2026-10-28, after Chad Holland gave the go-ahead. Selection run by Chad on his device. Every number above is pasted from `output/results.json` and `output_console.log`. Not reviewed line by line by Chad. Not independently reproduced.

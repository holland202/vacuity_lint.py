# E15 v2 run

`run_e15.py` scans the committed selection (`E15/selection/run/`) with the two pinned scanners and evaluates P1–P4 exactly as [PREREG_v2.md](../PREREG_v2.md) registers them.

Status: **NOT RUN.** This file and the script are committed before any scan, so their wording and code are timestamped ahead of the data.

## Decisions fixed now, before any scan

PREREG_v2.md leaves these points open. Each is settled here, before data, and is not revisited after.

1. **A selected commit that can no longer be fetched** (repository deleted, made private, or history rewritten) is recorded as UNAVAILABLE. It is excluded from the analysis and counted per arm. It is not replaced.
2. **P1 and P2 verdicts.** Each is a directional difference claim. It is CONFIRMED only if the medians differ in the predicted direction AND the registered two-sided Mann-Whitney test gives p < 0.05. Otherwise it is NOT CONFIRMED. P3 and P4 use their own registered rules unchanged.
3. **Bootstrap.** Each arm is resampled independently with replacement, 10,000 times, with `numpy.random.default_rng(20260908)` created fresh for each interval. The 95% interval is the 2.5–97.5 percentile.
4. **P4 splits.** `numpy.random.default_rng(20260908)` is created once. It draws permutations of Arm C until there are 1000 distinct unordered half-splits; a split and its complement count as the same split. Each split gets the same Mann-Whitney test.
5. **Mann-Whitney implementation:** `scipy.stats.mannwhitneyu`, two-sided, default method.
6. **Findings** means unsuppressed findings in the primary scanner's JSON.
7. **The `bench` descriptive count** sums the primary scanner's `verification_shaped` over each `.py` file whose relative path contains `bench` (case-insensitive), scanned one file at a time. It is descriptive only.
8. **Instrument defects.** A scanner traceback, or an exit code outside 0/1/2, is an instrument defect and VOIDS the run, as the freeze clause says. Both scanners' sha256 values are checked before the first scan, before every repository, and after the last.

## Deviation, recorded before the scan

PREREG_v2.md says the secondary scanner's text parser must be committed and tested on a fixture outside the pool **before selection**. It was not. The parser is in this script, committed after selection (`2539a4a` on `main`) but before any scan. The sensitivity analysis is still run, because it carries no verdicts and the parser reads three fixed summary lines. Its results are labelled as run in deviation from the registered timing. If the owner prefers, it can be reported as NOT RUN instead; that does not affect P1–P4.

## Self-test (SELF-TESTED, author's workspace)

`python run_e15.py --selftest` runs 10 checks, no network:

- exclusions remove exactly the registered paths
- the secondary parser reads, refuses garbage and repeated output, and handles an empty scan
- the instrument hash check rejects a wrong file
- a traceback counts as a defect
- P4 draws 1000 distinct splits and lands near 0.05 on one distribution
- the directional rule confirms a real shift but not a null or a wrong-direction shift
- P3 reaches each of CONFIRMED, REFUTED and INCONCLUSIVE
- Clopper-Pearson matches a known value

Eleven deliberate breakages of the script were each caught (exit 1). Both real pinned scanners were also run, through this script, on a small fixture outside the pool, including an empty tree.

## Pre-mortem

- **Repos changed since selection.** Each tree is fetched at its recorded commit, not at the current HEAD.
- **The run environment differs from the selection's.** The scan runs in Claude's cloud workspace (x86_64, Python 3.13); the selection ran on the owner's phone. Both scanners are pure Python and pinned by hash, so the counts should not depend on the platform, but that is untested here.
- **A scanner crash** voids the run; see decision 8.
- **P4 fails.** Every between-arm comparison is void, as registered, and is reported that way.

## Provenance

Script and README by Claude (Anthropic, Claude Opus 5.5), 2026-10-28, after Chad Holland gave the go-ahead for the scan. Not reviewed line by line by Chad. Not independently reviewed.

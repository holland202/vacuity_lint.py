# E15 v2 selection audit — 2026-10-28

Status: **SELF-TESTED.** The audit was run by Claude, the selection script's author, on the committed files. It is not an independent check. No scan has been run.

The selection ran on Chad Holland's device (Android 17, aarch64, Python 3.14.6) from 2026-10-28 09:03:45 to 09:14:19 UTC and was committed at `0a8681e`. The selection script is unchanged since its pre-run commit `7fa8adb`.

## Audit output

`python audit_selection.py E15/selection/run`, pasted verbatim:

```
PASS  search page HTTP 200
PASS  raw command carries the registered query verbatim
PASS  sort=stars, order=desc, per_page=100
PASS  selection order == API return order for all 61 records
PASS  stars in 5..50 and descending (50..50)
PASS  no forks or archived repos among processed items
PASS  every pool eligibility verdict matches its recorded clone/py count/owner
PASS  every eligible pool repo's arm matches its recorded CI paths
PASS  stopped at the first record where both strata hit 20 (record 61 of 61)
PASS  no duplicate repos in the processed results
INFO  ineligible pool repos by rule: {1: 10, 3: 1}
INFO  clone failure: order 26 after 120.1s: timeout after 120s
PASS  raw/arm_a_page_001.txt HTTP 200
PASS  raw/arm_a_page_002.txt HTTP 200
PASS  Arm A covers every public holland202 repo listed (27)
PASS  every Arm A verdict matches rules 1-3
INFO  Arm A: 21 eligible of 27; ineligible by rule {1: 6}; forks among eligible: 1; archived among eligible: 2
PASS  no tokens or Authorization headers in committed raw files or console log
PASS  every eligible repo has its exact 40-char commit recorded

16 passed, 0 failed
```

The audit can fail. On a copy of the run with one arm label flipped and the last two records swapped, it reported 3 failures (order, arm-vs-CI, stop point). That tampered copy was not committed.

## What the audit surfaced

1. **The sample is effectively 50-star repositories, not the 5..50 band.** All 61 processed repositories have exactly 50 stars. The registered rule sorts by stars descending and takes repositories in order. With about 252,000 matches, the stop point is reached long before the top of the 50-star tier runs out. The rules were followed exactly. The consequence is that E15's results describe repositories at the very top of the band, so limitation 5 of PREREG_v2.md is narrower in practice than it reads. Within the 50-star tie, the order is whatever GitHub returned; it is reproducible only from the saved raw page, not by re-running the query.
2. **Arm A and the pool differ on forks and archived repositories.** The pool query excludes both. Arm A, by the registration's wording ("every public repository owned by holland202"), includes them: 1 fork and 2 archived repositories are among Arm A's 21. This was decided by the registered wording, not after seeing data. It is recorded here so the asymmetry is visible.
3. **One clone timed out on the phone** (pool order 26, 120.1 s). It is recorded as an eligibility-3 failure, as registered. A server would likely have cloned it, so this is environment-dependent.
4. **The arms are unequal: B = 30, C = 20.** B filled faster before C reached 20. The registration allows this ("arm sizes are whatever the split produces").

None of these voids the selection under PREREG_v2.md. Items 1 and 2 belong in the results' limitations, written before any scan.

## Provenance

Audit script and this record by Claude (Anthropic, Claude Opus 5.5), 2026-10-28, at Chad Holland's direction. The selection itself was run by Chad on his device. Not independently reviewed.

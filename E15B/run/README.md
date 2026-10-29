# E15-B run

`run_e15b.py` scans the author's repositories at their 2026-07-27 commits with E15 v2's pinned scanners, and evaluates the classification, P1 and P2 exactly as [PREREG.md](../PREREG.md) registers them.

Status: **NOT RUN.** This file and the script are committed before any July commit is resolved and before any repository is scanned, so their wording and code are timestamped ahead of the data.

## Decisions fixed now, before any scan

PREREG.md leaves these points open. Each is settled here, before data, and is not revisited after.

1. **History clone.** Each repository is cloned with `git clone --filter=blob:none --no-checkout`, which gives the full commit history of the default branch the server reports, without file contents. The history clone is deleted after the July commit is found.
2. **July commit.** `git rev-list -1 --first-parent --before=2026-07-27T23:59:59Z HEAD`, as registered. G1 is then checked against `git log --first-parent --format='%H %ct' HEAD`: the commit's committer time is at or before the cutoff, and its first-parent child, if there is one, is after it.
3. **Trees and counts reuse E15's code, imported, not copied.** `fetch_tree` (a depth-1 fetch of the exact commit), `apply_exclusions`, `run_primary`, `run_secondary` and the instrument sha256 checks come from `E15/run/run_e15.py`. `count_py` and `failed_rule` come from `E15/selection/select_e15.py`, so eligibility rules 1–2 count `*.py` files before exclusions, as E15's selection did.
4. **A repository with no commit at or before the cutoff** is recorded as NO JULY COMMIT. It is not in Arm J and is not counted as UNAVAILABLE.
5. **UNAVAILABLE** means the history clone failed, or the July tree could not be fetched after one retry.
6. **G0** applies to every Arm J repository that has an E15 v2 scan record. Its E15 commit is fetched and scanned through the same `scan()` path as the July tree, with one retry if the fetch fails. A count that differs from E15 v2's recorded `verification_shaped` is a mismatch. A check that cannot run after the retry also VOIDS the run, the conservative reading of "one mismatch VOIDS the run". Arm J repositories with no E15 record are listed and not checked.
7. **P2's sign test:** `scipy.stats.binomtest(increases, increases + decreases, 0.5, alternative="two-sided")`, ties dropped. With no non-tied pairs, P2 is NOT CONFIRMED.
8. **M_J** is the mean of the primary instrument's `verification_shaped` over Arm J. An empty Arm J is reported as NO DATA, with no classification.
9. **Instrument defects** void the run, as in E15: a scanner traceback or an exit outside 0, 1 and 2 (E15's `_run`).
10. **No `--sabotage` switch.** PREREG.md registers G0 as the control that shows the pipeline can return high counts. A switch added after registration, whose outcome could match the real one, would add nothing a reader can rely on.
11. **DIGEST** is the sha256 of the canonical per-repository table (name, July commit, eligibility, July count, E15 count) plus the verdicts. RECORDED is pinned in a separate commit after the run, so `evaluate` then exits 0 only on the recorded outcome.

## Self-test (SELF-TESTED, author's workspace)

`python E15B/run/run_e15b.py --selftest` runs 17 checks, with no network. They cover:
- the classification bands and their edges;
- the G1 predicate in both directions;
- four sign-test cases, including ties and the wrong direction;
- July-commit resolution on local git repositories with fixed committer dates;
- a clone failure;
- every VOID path (G0 mismatch, G0 not checkable, G1);
- the eligibility filter, digest order-independence, and fork exclusion.

Ten deliberate breakages of the script were each caught (exit 1).

## Pre-mortem

- **History rewritten since July.** The commit that was the July head is missing from today's history. The registered definition then resolves to the newest surviving commit before the cutoff, which shows up as a July commit dated well before it. Every July commit's date is recorded. PREREG.md's own pre-mortem says such a repository would be counted UNAVAILABLE. That is wrong under its registered definition, which governs; the discrepancy is recorded here rather than worked around.
- **A default branch renamed or switched since July.** The run follows today's default branch, which may not be the branch the historical scan read. Recorded as a limitation; `default_branch` is saved per repository.
- **A scan that silently reads nothing** (an empty or wrong tree). That shows up as `files_scanned` 0 or a count far from E15's at G0. G0 catches a broken pipeline at E15's commits but not at July's.

## Provenance

Script and README by Claude (Anthropic, Claude Opus 5.5), 2026-10-29, after the owner delegated the session's path to Claude. Not reviewed line by line by Chad. Not independently reviewed.

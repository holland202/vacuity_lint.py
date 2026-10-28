# E15 v2 selection

`select_e15.py` draws E15's sample exactly as [PREREG_v2.md](../PREREG_v2.md) registers it. It **selects only**: it never runs `vacuity_lint` or any other scanner. Its output is committed to `E15/selection/run/` before any scan, as the registration requires.

Status: **SELECTION NOT RUN.** The script is committed first so its code is timestamped before the selection event.

## Where it runs, and why

It must run on the owner's device. Claude's cloud session can only call GitHub's API for repositories attached to that session, and the search API was refused there (HTTP 403, "sessions are bound to their configured repositories"). The refusal happened on a harmless test query (`repo:psf/requests`), so **the registered pool query has never been sent.** Nothing from the pool has been seen.

## What it does

1. Sends the registered query (`language:Python stars:5..50 pushed:>2025-09-08 fork:false archived:false`), sorted by stars descending, 100 per page. It fetches the next page only when the previous one is used up, and saves each raw response (headers and body) with its retrieval time under `run/raw/` before using it.
2. Takes repositories in returned order. Each gets a depth-1 clone with a 120 s limit, a count of `*.py` files, and eligibility rules 1–4. A clone failure is an eligibility-3 failure. Every repository processed is written to `run/progress.jsonl` as soon as it is decided.
3. Puts each eligible repository in Arm C if it has any registered CI path, otherwise Arm B. It stops the moment both arms reach 20, or at 200 eligible (shortfall), or when the results run out (shortfall).
4. Builds Arm A from every public `holland202` repository that passes rules 1–3. Forks and archived repositories are included, as the registration's wording requires; each is flagged.
5. Writes `selection.json`, `selection.csv`, `arm_a.json` and `run_meta.json`. Each record carries the exact commit cloned, so the later scan reads the same trees.

## Self-test (SELF-TESTED, author's workspace)

`python select_e15.py --selftest` runs 6 checks with no network:

- CI-path detection, both directions
- `.py` counting
- eligibility boundaries (4/5 files, 2000/2001, owner, rule order)
- the stop rule, simulated on fake results with a duplicate and ineligible items
- the 200-eligible shortfall rule, simulated

Seven deliberate breakages of the script were each caught by the self-test (exit 1). The checks were also run against real clones of non-pool repositories (`psf/requests`, and a nonexistent repository for the rule-3 path). The self-test does not cover the live GitHub search response format; that is seen for the first time in the real run.

## Pre-mortem (written before the run)

- **The phone sleeps or the network drops mid-run.** Use `termux-wake-lock` and Wi-Fi. If the run is interrupted, do **not** quietly re-run it: a second query returns different results. Commit what exists (`raw/` and `progress.jsonl`), then decide on a re-run in writing.
- **Slow mobile clones push repositories past 120 s.** They become eligibility-3 failures and are recorded, not retried. This is environment-dependent and is reported as such.
- **Storage.** Up to a few hundred depth-1 clones go to the clone directory given on the command line. Check free space first. Clones stay until the scan, which reads them by recorded commit.
- **API rate limits.** At most 10 search pages; the search limit is 30 a minute, so this should not bind. A refused page stops the run with the reason recorded.
- **Looking before committing.** The registration does not forbid reading the output, but the outputs are committed before any scan, and no repository is replaced, skipped or added after selection.

## Provenance

Script, self-test and this README were written by Claude (Anthropic, Claude Opus 5.5) on 2026-10-28, after Chad Holland gave the go-ahead for selection. Chad runs the selection on his device. The script has not been reviewed line by line by Chad, and it is not independently reviewed.

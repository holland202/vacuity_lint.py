# VL-FP-003 RESULTS: failure words inside data tables

**Status: EXECUTED (SELF-TESTED). R1–R5 held as registered; R6 left open by design.** Registration: [PREREG.md](PREREG.md), commit `6a38723`, made before the test or the fix. Failing test: commit `2e597d5`. Run 2026-10-27 in Claude's workspace, Linux x86_64, Python 3.13.17. Not yet reproduced on Chad's device, not independently reproduced.

## Failures first

- **The fix introduces a new false pass, by design.** A failure message stored inside a list (or tuple, set, dict) and printed later is no longer counted as failure text. If the file's name carries a verification hint (`verify_`, `check`, `test`…) it is still reported, downgraded from VL002 to VL001. If the name carries no hint, the file is missed entirely. Before the fix both cases were VL002. This is pinned by `test_known_blind_spot_is_recorded`, so any later change to the trade-off shows up as a test change rather than silently.
- **Two tests were added with the fix and were not registered:** the mutant test and the blind-spot test. On the unchanged scanner the mutant test ERRORS (`mock.patch.multiple` cannot patch `Scan.visit_Tuple`, which did not exist yet) and the blind-spot test FAILS (`verify_blind.py` gave `PRINTS_FAIL_ONLY`). Both are visible in [before/unittest.txt](results/before/unittest.txt). The registered R1 run predates them: [R1_unchanged_scanner.txt](results/R1_unchanged_scanner.txt).
- **The verification-shaped count moves**, not only the finding count: requests 10 → 9 and httpx 32 → 31, because the tables were verification-shaped only through their failure words. That count is E15's primary outcome. E15 is pinned at `e549dbf` and is not touched by this change, but any future E15 re-registration on a newer scanner inherits it.
- **The exploration repos were re-cloned for R5,** not the device's copies. The unchanged scanner gives exactly the device's counts on all five (37/10/1, 83/30/0, 91/44/1, 213/69/2, 60/32/1), so the comparison is like for like, and the exploration numbers now agree across aarch64/Termux/3.14 and x86_64/3.13.

## Results

| id | prediction | observed | verdict |
|---|---|---|---|
| R1 | unchanged scanner: A1, A2, G1, G2, G3 each `PRINTS_FAIL_ONLY` | all five `['PRINTS_FAIL_ONLY']` (fail_strings 3, 3, 1, 4, 1); test fails on A1 and A2, `failures=2`. [raw](results/R1_unchanged_scanner.txt) | HELD |
| R2 | after the fix: A1 and A2 no finding | `test_tables_are_not_findings` OK | HELD |
| R3 | after the fix: G1, G2, G3 still `PRINTS_FAIL_ONLY` | `test_guards_still_flagged` OK, including G3 (message held in a plain variable) | HELD |
| R4 | every existing check passes unchanged | selftest 20/20, exit 0; unittest 67 tests OK (before: the only failures were the VL-FP-003 tests); provenance_audit, mutation_probe and VLFP001 mutants exit 0 both sides; issue-7 mutants identical after masking temp paths. [before](results/before/) / [after](results/after/) | HELD |
| R5 | five repos: requests and httpx findings to 0, click and rich unchanged, total 5 → 3 | requests 1 → 0, httpx 1 → 0, flask 0 → 0, click 1 → 1, rich 2 → 2; total **5 → 3**. [raw](results/R5_five_repos.txt) | HELD |
| R6 | frequency of kind A in a random pool | not run; would preview E15's selection | OPEN |

## The change

- `Scan` gains `_data_depth`. `visit_Tuple`, `visit_List`, `visit_Set` and `visit_Dict` raise it while their children are visited; `visit_Constant` counts failure text only when it is zero.
- RULES.md gains one paragraph stating the rule and its blind spot.
- No rule ID, message, severity or exit code changed. `FAIL_WORDS` is unchanged.

## Doors (unrun)

- A printed JSON-style report, `print({"status": "FAILED"})`, is now not counted either. Same blind spot as above, different shape. Not measured on real code.
- Kind B (type-checking fixtures such as click's `tests/typing`) and kind C (benchmark and timing scripts counted as verification-shaped) remain false alarms. Each needs its own registration; kind C changes E15's primary outcome.
- R6, after E15 is resolved.

Prepared by Claude (Anthropic, Opus 5.5) at Chad Holland's direction, 2026-10-27. Human review level: direction only.

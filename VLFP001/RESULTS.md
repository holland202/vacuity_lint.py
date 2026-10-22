# VL-FP-001: results (appended after the fix; the registration is unchanged)

Registration: [PREREG.md](PREREG.md), commit `1d0956b`, written before any fix. Failing tests on the unfixed scanner: commit `eb62154` ([F1 output](results/F1_before_fix.txt)). Everything here is **self-tested** by its author (Claude, Anthropic, Opus 5.5). Human review level: direction only.

## Failures first (M8)

- **V-B withdrawn (registered as a fix; not delivered).** Treating `assert True` as a non-fail path made the frozen independent IE1 cases fail: `clean/verify_assert.py` and `blind/verify_always_assert.py` expect `assert True` files to scan clean. IE1 is independent evidence. Changing its expectations would rewrite someone else's record, so the guard was removed. V-B stays a documented blind spot. A test now pins that it still scans clean. Reclassifying it needs an owner decision and a new IE-aware registration.
- **F2 failed on the first fix attempt for V-C** ([attempt1.txt](results/attempt1.txt)). The swallow guard worked, but V-C still scanned clean for a different reason: the file was not "executable", because its only top-level statements are an assignment and a `try` block. **Post-hoc change E1:** a top-level `try`/`if`/`for`/`while`/`with` block that contains an `assert` or a call statement (outside nested defs) makes a file executable. Two post-hoc false-positive guards were added with it: G11 (an optional-import `try` in a library stays clean) and G12 (a version-check `if ... raise` in a gate library stays clean). E1 and G11/G12 were not registered, so they are labelled post hoc in the code and tests.

## Predictions

| ID | Outcome | Evidence |
|---|---|---|
| F1 | HELD | `FAILED (failures=8)` on `c9390d2`: V-A..V-D clean, CLI exit 0 |
| F2 | **PARTLY REFUTED** | V-A, V-D: finding + exit 1 after attempt 1. V-C: only after post-hoc E1. V-B: withdrawn (above) |
| F3 | HELD | G1–G10 clean (G11, G12 post hoc, also clean) |
| F4 | HELD | selftest 20/20; 58 unit tests OK; Issue-7 mutants 4/4; gate control PASS; fixture controls PASS; IE1 16 cases, 0 failures; provenance and mutation-probe selftests PASS |
| F5 | HELD (for the guards that shipped) | 4/4 mutants killed: tuple-assert, swallow, uncollected-test, top-level-block-executable (E1). The V-B guard did not ship |
| F6 | HELD | fixture-free self-scan: 0 findings, as before the fix |

Raw output: [results/after_fix.txt](results/after_fix.txt). Python 3.13.16 in a Linux container. Not run on the S25 or under Python 3.14.

## Scope and doors (M15)

- Out of scope, still open: V-E/F/G/J (coverage of hidden/skipped directories, extensionless scripts, symlinks), V-H (`sys.exit(main())` reachability) and V-I (`if False:` dead branches).
- `assert True` (V-B): an owner decision, since it touches IE1.
- The E15 pin and registration are untouched. Whether E15 runs on its original instrument or a newly registered one remains the owner's decision.

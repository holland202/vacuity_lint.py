# VL-FP-001: four static false passes, registered before the fix

**State:** REGISTERED. The fix is NOT written at the commit that adds this file.
**Instrument:** `vacuity_lint.py` at `main` `c9390d2` (2.0.1.dev0). This is an engineering change to the development instrument. It **does not touch the E15 pin** (`e549dbf…`), E15's registration or [E15/DEVIATIONS.md](../E15/DEVIATIONS.md). Whether E15 keeps its original instrument or gets a new registration remains the owner's decision.
**Authors:** Claude (Anthropic, Opus 5.5), at Chad Holland's direction (2026-10-22). Human review level: direction only. Self-tested (M10).
**Origin:** a registered probe on 2026-10-22 (Claude, self-run) found 4 Type A false passes. They are identical on `main` and PR #12. Each file below cannot fail, yet scans `clean`, exit 0:

| ID | Fixture | Why it cannot fail |
|---|---|---|
| V-A | `assert (x == 1, "msg")` | a non-empty tuple is always true |
| V-B | `assert True` as the only check | a truthy constant is always true |
| V-C | `try: assert x == 1` / `except AssertionError: print(...)` | the failure is swallowed |
| V-D | `def test_placeholder(): pass` in `verify_*.py` run as a script | pytest does not collect `verify_*.py`, and nothing calls it |

Out of scope here (separate work): coverage gaps for hidden or skipped directories, extensionless scripts and symlinks (V-E/F/G/J); reachability (V-H, `sys.exit(main())`); dead branches (V-I, `if False:`). These are documented limits.

## Predictions

- **F1 (before fix).** The new test file `tests/test_vlfp001.py` fails on `c9390d2`: V-A to V-D each still scan clean.
- **F2 (after fix).** V-A, V-B, V-C and V-D each produce a finding (VL001 or VL002) and exit 1 on the CLI.
- **F3 (no new false positives).** Each of these stays clean (no finding):
  - G1 `assert x == 1, "msg"`;
  - G2 `assert (a == b)`;
  - G3 `assert ()` (empty tuple: always fails, so it is a fail path);
  - G4 `assert False`;
  - G5 `try/except AssertionError` that re-raises;
  - G6 `try/except ValueError` around an assert;
  - G7 an assert inside a function *defined* in a `try` body;
  - G8 `def test_*` in `test_*.py`;
  - G9 `def test_*` in `verify_*.py` that imports `unittest` and calls `unittest.main()`;
  - G10 a `test_*` function in `verify_*.py` that the module calls.
- **F4 (no regressions).** All of these still pass:
  - `--selftest`;
  - `python3 -m unittest discover -s tests`;
  - `ci/check_issue7_mutants.py`, `ci/verify_gate.py`, `ci/verify_fixtures.py`;
  - the IE1 independent-case runner.
- **F5 (each guard is needed).** Removing any one of the four new guards (tuple, truthy constant, swallow, uncollected test) makes at least one new test fail.
- **F6 (self-scan).** A scan of the fixture-free repository tree reports no **new** finding compared with `c9390d2`.

A refuted prediction is kept and explained. It is not edited away.

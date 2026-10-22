# VL-FP probe — registered before running (2026-10-22, Claude Opus 5.5, self-authored, self-tested)
Instrument under test: vacuity_lint.py at PR #12 head ce32a82 (2.0.1.dev0).
A "false pass" = a file that cannot make its process exit nonzero (or never runs its check),
yet the scan returns status clean / exit 0.

| ID | Fixture | Predicted scanner result |
|---|---|---|
| C1 control | verify_plain.py: prints "[FAIL]", sys.exit(0) | VL002, exit 1 (instrument can say the other thing) |
| C2 control | verify_real.py: assert on a computed value | clean, exit 0 |
| V-A | tuple assert `assert (x == 1, "msg")` (always true) | clean exit 0 -> FALSE PASS |
| V-B | only `assert True` plus FAIL print | clean exit 0 -> FALSE PASS |
| V-C | assert inside try/except AssertionError: pass | clean exit 0 -> FALSE PASS |
| V-D | `def test_placeholder(): pass` in a script named verify_*.py run via __main__, prints FAIL, exits 0 | clean exit 0 -> FALSE PASS |
| V-E | vacuous verify script under `.github/scripts/` next to a clean file | clean exit 0, hidden file not counted -> COVERAGE FALSE PASS |
| V-F | vacuous verify script under `build/` next to a clean file | same as V-E |
| V-G | vacuous extensionless script `ci/verify` (shebang python) next to a clean file | not scanned -> COVERAGE FALSE PASS |
| V-H | `sys.exit(main())` where main() always returns 0 | clean -> FALSE PASS (documented reachability limit) |
| V-I | `if False: sys.exit(1)` | clean -> FALSE PASS (documented P12 blind spot) |
| V-J | symlinked directory containing a vacuous script | not followed -> COVERAGE FALSE PASS |
Each of V-E/F/G/J is run as "the vacuous file + one clean file" in one root, so files_scanned >= 1 and the empty-scan exit 2 cannot rescue it.
Refutation: any V row returning a finding (exit 1) or exit 2 refutes that row's prediction; it is kept as a null.

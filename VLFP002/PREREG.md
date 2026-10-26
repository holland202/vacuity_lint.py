# VL-FP-002: `pytest.fail()` is a fail path, registered before the change

**State:** REGISTERED. The scanner is unchanged at the commit that adds this file.
**Origin:** VL-ANTH-1 (2026-10-26), an exploratory scan of two public Anthropic Python repositories with this tool,
unchanged at `main` `e0a5aab` (2.0.1.dev0).
- In `anthropics/claude-agent-sdk-python` at `0e89b298e771259378a6cd3734e00d323dff5703`, `e2e-tests/conftest.py` was reported as VL001 `NO_FAIL_PATH`.
- Manual triage: the file fails through `pytest.fail(...)` when `ANTHROPIC_API_KEY` is missing, so the finding is a **false positive**.
- Cause, from the source: `has_fail_path` counts `assert`, `raise`, collectable `test_*` and nonzero exits; `Scan.visit_Call` recognizes only `sys.exit`, `os._exit` and `os.abort`.
- Controlled reproduction: two `check_math.py` files with a `__main__` block, identical except for the failing line. `pytest.fail("value is wrong")` gives 1 finding; `raise SystemExit(1)` gives 0.
- A search of the repository's code, docs and issue #7 found no earlier record of this blind spot.

**Instrument:** `vacuity_lint.py` at `main` `e0a5aab`. This does not touch the E15 pin (`e549dbf…`).
**Authors:** Claude (Anthropic, Opus 5.5), at Chad Holland's direction (2026-10-26). Human review level: direction
only. **Self-tested.**

## The change

`pytest.fail(...)` counts as a fail path, the same way `raise` does, when `pytest` is the real module. That is
decided with the same conservative binding rule already used for `sys` and `os` (`_exit_bindings`). There are two
recognized forms:
- `import pytest` / `import pytest as <name>`, then `<name>.fail(...)`;
- `from pytest import fail` / `from pytest import fail as <name>`, then `<name>(...)`.

The binding must be a trusted top-level import that is not shadowed anywhere in the file. Otherwise the call does
**not** count.

The following stay the same:
- every rule ID, code, message, severity, category and exit code;
- `pytest.skip`, `pytest.xfail` and `pytest.exit` (none of them is added; `pytest.exit` is not a test failure);
- `unittest`'s `self.fail()` (left as a registered door; see below);
- the `--help` text and RULES.md wording, apart from one added line naming `pytest.fail()` as a fail path.

## Predictions (fixed before the test or the fix exists)

Cases are scanned as fresh files by the imported scanner, in a new `tests/test_vlfp002.py`. Each case is a file named
`check_case.py` with a `__main__` block, so it is verification-shaped.

| id | case | expected after the fix |
|---|---|---|
| C1 | `import pytest`, then `pytest.fail("x")` | 0 findings |
| C2 | `import pytest as pt`, then `pt.fail("x")` | 0 findings |
| C3 | `from pytest import fail`, then `fail("x")` | 0 findings |
| C4 | `from pytest import fail as die`, then `die("x")` | 0 findings |
| N1 | no fail path at all (prints only) | 1 finding (VL001) |
| N2 | a local class with a `.fail()` method, called as `obj.fail("x")` | 1 finding |
| N3 | `import pytest`, but `pytest = Helper()` elsewhere in the file, then `pytest.fail("x")` | 1 finding (shadowed) |
| N4 | a local `def fail(msg): print(msg)`, then `fail("x")` | 1 finding |
| N5 | `import pytest`, then `pytest.skip("x")` only | 1 finding |

- **R1 (control, before the fix):** on the unchanged scanner, C1–C4 each give **1 finding**, so the new test fails on exactly those four, and N1–N5 give 1 finding each. This shows the test can fail.
- **R2:** after the fix, C1–C4 give 0 and N1–N5 give 1. The new test passes.
- **R3:** with the fix in place but the new recognition disabled by a mutant (`VLFP002_DISABLE` patch applied in the test), C1–C4 return to 1 finding.
- **R4:** nothing else changes. Compared byte for byte with `VLFP002/results/before/` (recorded on `e0a5aab` before this file):
  - `--selftest` stays 20/20;
  - `unittest discover -s tests` goes from 60 tests to 60 plus the new module's tests, all OK;
  - `ci/check_issue7_mutants.py`, `VLFP001/mutants.py`, `ci/verify_gate.py`, `ci/verify_fixtures.py`, the IE1 independent runner, `provenance_audit.py --selftest` and `mutation_probe.py --selftest` all exit 0, with identical output.

  The only allowed differences are counts that include the new test module's own lines.
- **R5 (re-run of VL-ANTH-1, same commits):**
  - `anthropic-sdk-python` stays at 0 findings.
  - `claude-agent-sdk-python` goes from 2 findings to **1**: `conftest.py` disappears, and `examples/stderr_callback_example.py` (VL002, a separate false positive) stays.

## Not changed here (door, registered unrun)

`unittest.TestCase.fail()` (`self.fail(...)`) is very likely the same blind spot inside `TestCase` methods. It is
not tested and not changed here.

## Stopping rule

If R1 does not hold, meaning the test does not fail on the unchanged scanner, stop: the test is not measuring the
defect. If R4 shows any other difference, stop and report; do not adjust the change to hide it.

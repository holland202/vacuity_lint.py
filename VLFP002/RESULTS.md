# VL-FP-002 RESULTS: `pytest.fail()` as a fail path

**Status: EXECUTED (SELF-TESTED). R1–R5 held as registered.** Registration: [PREREG.md](PREREG.md), commit `8ecfb02`,
made before the test or the fix. Failing test: commit `b9aff56`. Run 2026-10-26, Linux x86_64, Python 3.13.17.
Not independently reproduced.

## Failures first

- **R1's mutant test errored on the unchanged scanner rather than failing.** `mock.patch.object` raised
  `AttributeError` because `Scan._is_pytest_fail` did not exist yet. This was expected and is recorded, not hidden.
  The registered R1 check, C1–C4 failing on the unchanged scanner, held separately.
- **The origin finding was itself mine to verify.** VL-ANTH-1 reported 2 findings in Anthropic's agent SDK, and both
  were false positives. This fix removes one of them (`conftest.py`). The other (`examples/stderr_callback_example.py`,
  VL002 on an example script) is **not** addressed and stays a false positive.

## Results

| id | prediction | observed | verdict |
|---|---|---|---|
| R1 | unchanged scanner: C1–C4 give 1 finding each, N1–N5 give 1 each | C1–C4 `['NO_FAIL_PATH']` (4 FAIL); lookalike test OK; mutant test ERROR (see above). [raw](results/R1_unchanged_scanner.txt) | HELD |
| R2 | after the fix: C1–C4 give 0, N1–N5 give 1 | 3 tests OK. [raw](results/R2_R3_after_fix.txt) | HELD |
| R3 | recognition disabled by mutant: C1–C4 back to 1 | mutant test OK | HELD |
| R4 | nothing else changes | selftest, provenance, IE1 runner, verify_fixtures and VLFP001 mutants **byte-identical**. issue-7 mutants and mutation_probe identical after masking random temp paths. unittest 60 → 63 (the 3 new tests). verify_gate +1 file scanned and +1 verification-shaped (the new test module), still clean and exit 0. [before](results/before/) / [after](results/after/) | HELD |
| R5 | re-scan of VL-ANTH-1's commits | `anthropic-sdk-python@202db72`: 0 findings, exit 0. `claude-agent-sdk-python@0e89b29`: **2 → 1**; `conftest.py` gone, the stderr example remains. [raw](results/R5_claude-agent-sdk-python.txt) | HELD |

## The change

- `_exit_bindings` also tracks `pytest`: a top-level `import pytest [as x]`, and `from pytest import fail [as y]`. The existing trusted-and-unshadowed rule applies unchanged.
- New `Scan._is_pytest_fail`: a matching call counts as a `raise`.
- `--help` and RULES.md each gain one line.
- No rule ID, message, severity or exit code changed.

## Doors (unrun)

- `unittest`'s `self.fail()` inside `TestCase` methods is likely the same blind spot. Not tested.
- `examples/stderr_callback_example.py` in the agent SDK: VL002 counts failure-oriented text in a non-check demo
  script. Whether example scripts should be verification-shaped at all is a separate question.

Prepared by Claude (Anthropic, Opus 5.5) at Chad Holland's direction, 2026-10-26. Human review level: direction only.

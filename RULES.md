# Vacuity Lint — Rule reference (2.0.1.dev0, unreleased)

Vacuity Lint is a **file-level, heuristic** Python AST scanner. Findings are
**review prompts**, not assertions that a test is incorrect or that a fail
branch is reachable. The scanner does not run inspected source files and has
no third-party runtime dependencies.

## Verification-shaped selection

The scanner considers Python files for its four heuristic rules when they
either declare a function whose name begins `test_`, or satisfy **both**:

1. Have a top-level `if __name__ == "__main__"` (either equality order), or a
   top-level expression statement that is a function call; and
2. Have any of these filename substrings: `test`, `check`, `verify`,
   `smoke`, `validate`, `gate`, `audit`, `selftest`, `assert`,
   `prove`, `harness`; **or** contain an AST string constant with one
   of the failure-oriented substrings below.

The failure-text heuristic inspects **all AST string constants**, not only
`print()` arguments. Substrings (case-insensitive) are `[fail]`, `fail:`,
`failed`, `[error]`, `mismatch`, and `does not match`.
Comments are not parsed as AST strings, but module docstrings are.

This deliberately misses some verification tools that don't use those signals.
Conversely, a verification-like name or an example in a docstring can cause
a false positive. An ordinary utility containing `sys.exit(0)` is **not**
automatically considered a broken check.

## Stable rule IDs

IDs persist independently of message wording, and are available through
`vacuity-lint --format json PATH`. Severity is **descriptive only**;
`warning` means heuristic review, `error` means analysis was prevented.
There is no calibrated probability or automated correctness score.

| ID | Code | Category | Severity | Trigger and intent |
| --- | --- | --- | --- | --- |
| VL001 | `NO_FAIL_PATH` | heuristic | warning | Verification-shaped file with no recognized `assert`, `raise`, `test_` function, or nonzero/dynamic exit; if it contains a failure string the more specific VL002 is used |
| VL002 | `PRINTS_FAIL_ONLY` | heuristic | warning | Verification-shaped file containing a failure-oriented **string constant** but no recognized failure path (name is historical; the string need not be printed) |
| VL003 | `UNCOLLECTABLE_TEST` | heuristic | warning | File named `test_*.py` with no `test_` function and no recognized fail path; may coexist with VL001/VL002 |
| VL004 | `ALWAYS_EXITS_ZERO` | heuristic | warning | Verification-shaped file with exit calls all classified as literal zero, no recognized assert/raise/test function and no failure-string signal |
| VL005 | `UNPARSEABLE` | analysis_error | error | Python AST parsing failed; CLI filesystem coverage failures are reported separately in `coverage_errors` |

**What does not count as a fail path (VL-FP-001, unreleased):**
- an `assert` whose test is a non-empty tuple, e.g. `assert (x == 1, "msg")`, which is always true;
- an `assert` inside a `try` whose handler catches `AssertionError` (or `Exception`/`BaseException`/bare) and neither re-raises nor calls an exit-like function;
- a `def test_*` in a file pytest does not collect by default (not `test_*.py` / `*_test.py`), with no `unittest`/`pytest` import and no reference in the module.

A top-level `try`/`if`/`for`/`while`/`with` block containing an `assert` or a call statement now makes a file executable.

`assert True` is still counted, as a documented blind spot recorded by the independent IE1 cases. Details: [VLFP001/RESULTS.md](VLFP001/RESULTS.md).

Recognized fail-path shapes include any `assert`, non-`SystemExit` `raise`,
`raise SystemExit(nonzero)`, `sys.exit(nonzero)`, `os._exit(nonzero)`,
`quit(nonzero)`, `exit(nonzero)`, or an exit with a dynamic expression,
plus declarations of `test_*` functions (including methods). This is a
**syntactic** inventory, not control-flow reachability analysis. In particular,
a conditional or unreachable `raise` still counts as a potential fail path,
and bare `raise SystemExit`, `SystemExit()`, `SystemExit(0)` and
`SystemExit(None)` are treated as successful rather than failing.

Simple top-level `import sys/os as ...`, `from sys import exit as ...`, and
`from os import _exit/abort as ...` aliases are recognized. `os.abort()` is
a possible nonzero termination. Names assigned, deleted, imported from
another module, or shadowed by a parameter/definition/pattern anywhere in
the file are conservatively excluded from this recognition. This can
produce false positives across separate scopes. Dynamic rebinding,
attribute replacement, wildcard imports and general Python name resolution
are not analyzed. These remain heuristic shapes, not execution proofs.

## Examples

**VL002, detected**

```python
# verify_model.py
print("[FAIL] model check")
```

**VL004, detected**

```python
# verify_example.py
import sys
sys.exit(0)
```

**Valid conditional nonzero exit, no finding under this heuristic**

```python
# verify_example.py
import sys
ok = False
sys.exit(0 if ok else 1)
```

**Plain utility ending successfully, not assumed verification**

```python
# ordinary.py
import sys
sys.exit(0)
```

**Documented blind spot**

```python
def verify_something():
    assert True   # vacuous, yet recognized as a syntactic fail path
```

This tool is **not** a mutation tester or Type-B unreachable-path analyzer.

## Suppression

In the affected file, include a **reason**, e.g.:

```python
# vacuity-lint: intentional - hardware probe is advisory only, never a CI gate
```

The reason is required and must be nonempty. Suppression operates at the
**whole-file level**, not per rule or line: all findings for that file are
listed separately as intentional, along with the reason. A bare
`# vacuity-lint: intentional` does nothing. We do **not** offer an
unjustified repository-wide ignore list.

## JSON schema and exit behavior

```sh
vacuity-lint ./project --format json
```

Representative structure (paths and messages vary; **no line is supplied**
because the present detector scores files, not precise AST locations):

```json
{
  "tool": "vacuity-lint",
  "version": "2.0.1.dev0",
  "status": "findings",
  "files_scanned": 1,
  "verification_shaped": 1,
  "findings": [
    {
      "rule_id": "VL002",
      "rule": "PRINTS_FAIL_ONLY",
      "severity": "warning",
      "category": "heuristic",
      "path": "verify_model.py",
      "message": "contains failure text 1x but has no assert, raise, or nonzero exit",
      "suppressed": false
    }
  ],
  "suppressions": [],
  "coverage_errors": []
}
```

The emitted JSON object is deterministic in key order; `findings` and
`suppressions` are sorted for JSON output. `--quiet` affects only text mode;
JSON always contains the complete machine-readable report.

The **exit code contract** for text and JSON is:

- `0`: at least one Python file scanned, no **unsuppressed** findings or coverage errors.
- `1`: unsuppressed findings, including syntax-error VL005, with no coverage error.
- `2`: no Python files scanned, or any requested root/traversal/read failed.

Coverage errors take precedence over findings and produce JSON status
`analysis_error` with `coverage_errors: [{"path": "...", "message": "..."}]`.
Successfully obtained findings and suppressions are retained. The
`files_scanned` count includes enumerated files whose read or parse failed;
it does not certify complete coverage. Hidden/configured directories and
directory symlinks are not recursively followed. Filesystem changes during
enumeration are not an atomic snapshot guarantee.

CLI-usage errors (such as an invalid `--format` value) also use argparse's
exit code `2` and are written to stderr, not as a scanner JSON report.

A finding is a **review prompt**; CI integration should decide explicitly
whether code 1 blocks a build. Use of `|| echo ...` can hide a CI failure,
so review any shell fallback carefully. Per-user-configurable failure policy
(`--fail-on`), SARIF, custom rules, and repository-wide suppressions are **not
included** in this release.

## Corresponding regression evidence

- Built-in P1–P3: detection of missing paths and print-only failures.
- Built-in P4–P8: legitimate control tests that stay unflagged.
- Built-in P9/P10, P19/P20: detector can return both clean/finding and refuses
  to declare an empty tree clean.
- Built-in P11–P18: malformed files, explicit blind spot, suppressions.
- `tests/test_exit_precision.py`: 13 distinct exit-style/entry-point cases.
- `tests/test_json_cli.py`: CLI version, JSON, rule metadata, suppressions,
  syntax errors and stable legacy text/exit behavior.
- `tests/test_scan_integrity.py`: missing roots, incomplete traversal/read,
  real permission denial where supported, lexical suppressions and bare SystemExit.
- `tests/test_exit_aliases.py`: imported exits, shadowing and precise literal exits.
- `tests/test_gate_control.py`: real clean/planted/clean control plus constant,
  unrelated-finding, malformed-output and scan-error substitutes.
- `ci/check_issue7_mutants.py`: four deliberate scanner regressions must fail
  their intended assertions; crashes/import errors do not count as detection.

These tests do not demonstrate real-world precision rates on unrelated
repositories. Submit minimal reproducible false positives/false negatives
through GitHub Issues.

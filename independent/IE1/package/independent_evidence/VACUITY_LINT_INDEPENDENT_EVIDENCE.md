SANITIZED DISTRIBUTION COPY — local paths/private archive references redacted. Historical record; see MAINTAINER_HANDOFF.md for portable commands and qualifications.

# Vacuity Lint v2.0.0 — Independent Verification Evidence

**Repository:** <https://github.com/holland202/vacuity_lint.py>  
**Evaluator:** Putluru Sandeep (`sunny-kavixo`)  
**Verification date:** 2026-10-18  
**Scope:** Local, read-only verification of the maintainer-requested findings
and recovered prior evaluation inputs.  
**Publication status:** Local evidence only. No commit, push, pull request,
issue, release, or external submission was made.

## Executive result

The evaluated checkout is Vacuity Lint `main` at
`da5fe76ddcd660c2d21a89853623e905a0b33708`, one commit after the `v2.0.0`
release tag target `c31330e8baaf44ef6610b26272c0ab8910e610be`. The checked source
file is `vacuity_lint.py` version `2.0.0`, SHA-256:

```text
3cb0d07d4d5b807132a6a82bef50e09051d4fab35e00449e4cf435745a406971
```

### Newly executed checks

| Check | Result | Provenance |
|---|---:|---|
| Embedded Vacuity self-test | **20/20 passed** | Newly executed |
| Repository regression tests | **24/24 passed** | Newly executed |
| Installed release contract | **13/13 passed** | Newly executed through `runpy` from the isolated evidence directory; see note below |
| Mutation probe self-test | **PASS**; KILLED/SURVIVED/CRASHED observed | Newly executed |
| Provenance audit self-test | **PASS**; reconstructible/not-reconstructible observed | Newly executed |
| Recovered independent cases | **16/16 expected classifications** | Newly re-executed |
| Seven copied EGRR scripts | **7/7 clean; exit 0; no findings** | Newly re-executed |
| Docstring reproduction | **Confirmed**: VL002, exit 1 | Newly executed |
| Empty pytest function | **Confirmed limitation**: scanner clean, exit 0; pytest 1 passed | Newly executed |
| Unreachable `raise` | **Confirmed limitation**: scanner clean, exit 0; target ran successfully | Newly executed |

The original evidence was recovered from the existing temporary evaluation
workspace and archive references. It was not silently treated as a new run.
The recovered 16-case fixtures and seven EGRR copies were hash-checked before
the newly executed reruns.

## Safety and workspace boundary

The existing evaluation workspace was found at:

```text
<ORIGINAL_EVALUATION_WORKSPACE>/
```

The repository under test is its `repo/` child. The evidence package is inside
the isolated workspace at:

```text
<ORIGINAL_EVALUATION_WORKSPACE>/independent_evidence/
```

Only files inside the evidence directory were created for this task. The
Vacuity repository was not edited. No
Principia Artificialis, Sunny Local AI, or LittleBit files were changed. No
expensive benchmark, scientific experiment, commit, push or external
publication was performed.

The repository checkout was clean at the start of the verification. The
isolated workspace contains an empty, untracked `vacuity_lint.egg-info/`
directory left by the earlier evaluation setup. It was not removed or changed.
That directory affects the release-smoke script if it is launched directly
from the repository path; the successful release-contract result below was
run without modifying it, using `runpy` from the evidence directory.

## Recovered evaluation workspace and provenance

### Repository facts

```text
Remote: https://github.com/holland202/vacuity_lint.py.git
Branch: main
HEAD: da5fe76ddcd660c2d21a89853623e905a0b33708
Describe: v2.0.0-1-gda5fe76
v2.0.0 tag: c31330e8baaf44ef6610b26272c0ab8910e610be
HEAD parent: c31330e8baaf44ef6610b26272c0ab8910e610be
HEAD author: Chad Holland
HEAD date: 2026-10-16T19:10:28-05:00
HEAD subject: ci: retire v2.0.0 release publisher after successful release
Package version: 2.0.0
Python requirement: >=3.10
Runtime dependencies: none
```

The `v2.0.0` tag and evaluated `main` commit are deliberately distinguished:
the release tag points to `c31330e`, while the current evaluated source is the
post-release `da5fe76` commit.

### Recovered 16 constructed cases

The original driver is:

```text
../independent_cases/run_independent.py
```

The final fixture inventory was recovered as follows:

- Clean: 5 cases.
- Defective: 4 cases.
- Documented blind spots: 4 cases.
- Heuristic edge cases: 3 cases.
- Total: 16 cases.

The final driver records these expected classifications:

```text
clean/test_real.py                 exit 0; no rules
clean/verify_assert.py             exit 0; no rules
clean/verify_dynamic_exit.py       exit 0; no rules
clean/ordinary.py                  exit 0; no rules
clean/verify_suppressed.py         exit 0; one recorded suppression
defective/verify_prints.py         exit 1; VL002
defective/test_empty.py            exit 1; VL001, VL003
defective/verify_zero.py           exit 1; VL004
defective/test_broken.py           exit 1; VL005
blind/verify_unreachable_raise.py exit 0; no rules
blind/verify_always_assert.py     exit 0; no rules
blind/verify_dead_exit.py         exit 0; no rules
blind/test_empty_function.py      exit 0; no rules
edge/verify_doc_fail.py            exit 1; VL002
edge/check_module.py               exit 1; VL001
edge/validate_library.py           exit 0; no rules
```

The final recovered run occurred after `blind/test_empty_function.py` was
added. An earlier recorded run had 15 cases; this package uses and reruns the
final 16-case set. The recovered case inputs are not newly authored by this
task.

The prior archive also records the final fixture set and hashes at:

```text
<PRIVATE_ARCHIVE_REFERENCE_REMOVED>
```

The current temporary workspace is the directly usable copy for reruns; the
archive path is provenance context, not a substitute for the fixture files.

### Recovered seven EGRR scan inputs

The seven files were copied previously from the Principia checkout into:

```text
../independent_cases/egrr_copies/
```

The source files were originally taken from these read-only locations:

```text
<ORIGINAL_EGRR_CHECKOUT>/reproducibility/egrr_desc_001_termux/termux_verify.py
<ORIGINAL_EGRR_CHECKOUT>/reproducibility/egrr_desc_001_termux/registered_fixture_gate.py
<ORIGINAL_EGRR_CHECKOUT>/reproducibility/egrr_desc_001_termux/noise_probe.py
<ORIGINAL_EGRR_CHECKOUT>/reproducibility/egrr_desc_001_termux/test_termux_verify.py
<ORIGINAL_EGRR_CHECKOUT>/experiments/egrr_issue28/test_egr2_integration.py
<ORIGINAL_EGRR_CHECKOUT>/experiments/egrr_issue28/descriptive_reporting_gate.py
<ORIGINAL_EGRR_CHECKOUT>/experiments/egrr_issue28/test_verified_aggregate.py
```

The source/copy integrity rerun reported `exact=True` for every file. The
copy SHA-256 values are:

```text
termux_verify.py             b6bdaffa27c34940d7453d32e957399853f090eabe8185b543049ebb8d1f4950
registered_fixture_gate.py   df852c993f212e87f8af55f52ea97231644afd9d9cf37242f47a6afe6f70d33d
noise_probe.py               789ed18ed295b25c28eef7270ceae65b278188ef98476174b7a2680c6eb19bd6
test_termux_verify.py        be08298d1b97a24b30056a3989292977737f8dcba70e692a5dcb8f3236dc106c
test_egr2_integration.py     5f8fad442bd2c144358bba6001cb9fc7ff505608209e71c707cfeaed61100987
descriptive_reporting_gate.py 5492a13d6ddb75e73e95f83c7e848174797d43af27ce5bf703b4e436c6c1a526
test_verified_aggregate.py   8f46b13e9ced0e354b954781fc7321fc97c0a49c2874c39a183cb79029491f03
```

The recovered copies are scanned read-only. They are not the adjacent
Principia EGRR test results and must not be confused with the EGRR
`termux-verification.json` manifest.

## Three requested findings

Each reproduction below uses a minimal source file in `reproductions/`. The
scanner command analyzes the file; it does not execute the target source. The
target execution command is included separately where it helps demonstrate the
semantic result.

### Finding A — VL002 docstring false positive

**Classification:** Confirmed heuristic false positive / implementation bug
against the semantic meaning of `PRINTS_FAIL_ONLY`. Proposed improvement:
ignore module and function docstrings when counting emitted failure text, and
prefer inspecting string arguments in actual output/logging calls. The current
heuristic can also be improved by distinguishing documentation literals from
runtime-emitted strings.

**Fixture:** `reproductions/vl002_docstring.py`

```python
"""Documentation mentions a [FAIL] result, but this is a clean demo."""

if __name__ == "__main__":
    print("documentation loaded")
```

SHA-256:

```text
a71de498c0e9997d0cbc153b8f29bce1cbc2eee5b4f731830037407fc46f6d89
```

**Expected behavior:** A clean executable demo whose only runtime output is
`documentation loaded` should not be reported for printing failure text.

**Scanner command:**

```bash
PYTHONDONTWRITEBYTECODE=1 \
  "$VENV/bin/python" "$REPO/vacuity_lint.py" \
  "$EVIDENCE/reproductions/vl002_docstring.py"
```

**Actual scanner result:** exit status `1`; `VL002` / `PRINTS_FAIL_ONLY`.

Exact stdout:

```text
python files scanned    : 1
verification-shaped     : 1
findings                : 1
declared intentional    : 0

PRINTS_FAIL_ONLY  (1)
  reproductions/vl002_docstring.py
      prints failure text 1x but has no assert, raise, or nonzero exit
```

Exact stderr: empty.

**Runtime control:**

```bash
PYTHONDONTWRITEBYTECODE=1 \
  "$VENV/bin/python" "$EVIDENCE/reproductions/vl002_docstring.py"
```

Actual runtime result: exit status `0`, stdout `documentation loaded`, stderr
empty. The scanner is therefore reacting to the docstring constant, not to an
emitted failure message.

**Technical explanation:** `Scan.visit_Constant()` increments `fail_strings`
for every string constant containing a configured failure token. The module
docstring contains `[FAIL]`; `looks_like_verification()` then treats the
executable `verify`-shaped file as a candidate and the analysis emits VL002.
This is a concrete false positive, not evidence that the target program is
vacuous.

### Finding B — empty pytest function accepted

**Classification:** Documented limitation, not a proven defect in the stated
static scope. Proposed improvement: add a separate advisory for test functions
whose bodies contain no meaningful assertion or failure-producing call, while
clearly labeling it heuristic. Mutation testing or test execution would still
be needed to assess whether a test meaningfully checks its intended behavior.

**Fixture:** `reproductions/empty_pytest.py`

```python
def test_empty():
    pass
```

SHA-256:

```text
a1ca1056104f7a80576fa1ab1953a8469a0c277b6c1787faf808e944d7495e80
```

**Expected behavior:** The function is collected by pytest and passes, but it
contains no assertion and does not meaningfully verify a condition. Vacuity
Lint should not be described as proving that the test is useful.

**Scanner command:**

```bash
PYTHONDONTWRITEBYTECODE=1 \
  "$VENV/bin/python" "$REPO/vacuity_lint.py" \
  "$EVIDENCE/reproductions/empty_pytest.py"
```

**Actual scanner result:** exit status `0`; no findings.

Exact stdout:

```text
python files scanned    : 1
verification-shaped     : 1
findings                : 0
declared intentional    : 0

no vacuous verification found
```

Exact stderr: empty.

**Pytest control command:**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  "$EVIDENCE/reproductions/empty_pytest.py"
```

Actual pytest result: exit status `0`.

```text
.                                                                        [100%]
1 passed in 0.00s
```

**Technical explanation:** the scanner treats any `def test_*` as a possible
failure path (`has_fail_path()` returns true when `test_defs > 0`). It does not
inspect whether the body contains an assertion, meaningful call, or reachable
failure condition. The README explicitly says the tool does not prove tests are
correct, and the result is consistent with that boundary.

### Finding C — unreachable failure path is not detected

**Classification:** Confirmed documented limitation. Proposed improvement:
control-flow/reachability analysis, constant-condition reasoning, or mutation
testing that demonstrates whether the failure branch can affect the verdict.
The existing AST scan intentionally recognizes the syntactic `raise` without
proving that execution can reach it.

**Fixture:** `reproductions/verify_unreachable_raise.py`

```python
if __name__ == "__main__":
    if False:
        raise RuntimeError("unreachable")
    print("success")
```

SHA-256:

```text
681f1c595ca982f58b4c7b4287277543d87d854a5cbf88cd1d120879b096fb44
```

**Expected behavior:** The `raise` is syntactically present but unreachable;
the checker should report the documented blind spot rather than treating clean
output as proof of a live failure path.

**Scanner command:**

```bash
PYTHONDONTWRITEBYTECODE=1 \
  "$VENV/bin/python" "$REPO/vacuity_lint.py" \
  "$EVIDENCE/reproductions/verify_unreachable_raise.py"
```

**Actual scanner result:** exit status `0`; no findings.

Exact stdout:

```text
python files scanned    : 1
verification-shaped     : 1
findings                : 0
declared intentional    : 0

no vacuous verification found
```

Exact stderr: empty.

**Runtime control command:**

```bash
PYTHONDONTWRITEBYTECODE=1 \
  "$VENV/bin/python" "$EVIDENCE/reproductions/verify_unreachable_raise.py"
```

Actual runtime result: exit status `0`, stdout `success`, stderr empty.

**Technical explanation:** the AST contains a `raise`, so `has_fail_path()`
returns true. The scanner does not evaluate `if False` or construct a control-
flow graph. Its clean result confirms the documented Type-B reachability blind
spot; it does not establish that the verification is sound.

## Finding classification summary

| Finding | Observed behavior | Classification | Safe engineering response |
|---|---|---|---|
| VL002 docstring | Documentation `[FAIL]` token produces a finding even though runtime emits only `documentation loaded` | Confirmed heuristic false positive / bug | Exclude docstrings and distinguish runtime output contexts |
| Empty pytest function | `pytest` reports `1 passed`; scanner reports clean | Documented limitation | Optional advisory for assertion-free tests; do not claim test correctness |
| Unreachable `raise` | Scanner sees syntactic `raise`; runtime reaches only success path | Documented limitation | Add reachability analysis or mutation-based complementary checks |

## Recovered 16-case rerun

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  "$VENV/bin/python" "$CASES/run_independent.py" \
  "$REPO/vacuity_lint.py" "$CASES"
```

The driver itself compares actual exit codes and rule IDs against the recovered
expected classifications. Newly executed stdout:

```text
PASS clean/test_real.py: exit=0, rules=[], status=clean
PASS clean/verify_assert.py: exit=0, rules=[], status=clean
PASS clean/verify_dynamic_exit.py: exit=0, rules=[], status=clean
PASS clean/ordinary.py: exit=0, rules=[], status=clean
PASS clean/verify_suppressed.py: exit=0, rules=[], status=clean
PASS defective/verify_prints.py: exit=1, rules=['VL002'], status=findings
PASS defective/test_empty.py: exit=1, rules=['VL001', 'VL003'], status=findings
PASS defective/verify_zero.py: exit=1, rules=['VL004'], status=findings
PASS defective/test_broken.py: exit=1, rules=['VL005'], status=findings
PASS blind/verify_unreachable_raise.py: exit=0, rules=[], status=clean
PASS blind/verify_always_assert.py: exit=0, rules=[], status=clean
PASS blind/verify_dead_exit.py: exit=0, rules=[], status=clean
PASS blind/test_empty_function.py: exit=0, rules=[], status=clean
PASS edge/verify_doc_fail.py: exit=1, rules=['VL002'], status=findings
PASS edge/check_module.py: exit=1, rules=['VL001'], status=findings
PASS edge/validate_library.py: exit=0, rules=[], status=clean

independent_cases=16 failures=0
```

Process exit status: `0`. Stderr: empty.

This is a black-box classification run against the cloned scanner. It confirms
the driver’s expected outputs; it does not establish that the expectations are
scientifically or semantically complete.

## Seven EGRR script scan rerun

The copied EGRR scripts were scanned without changing their contents:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  "$VENV/bin/python" "$REPO/vacuity_lint.py" --format json \
  "$CASES/egrr_copies"
```

Directory-level result:

```json
{
  "files_scanned": 7,
  "findings": [],
  "status": "clean",
  "suppressions": [],
  "tool": "vacuity-lint",
  "verification_shaped": 6,
  "version": "2.0.0"
}
```

Process exit status: `0`. Stderr: empty.

The per-file rerun produced:

```text
descriptive_reporting_gate.py  exit=0  status=clean  verification_shaped=1  rules=[]  stderr_empty=True
noise_probe.py                 exit=0  status=clean  verification_shaped=0  rules=[]  stderr_empty=True
registered_fixture_gate.py     exit=0  status=clean  verification_shaped=1  rules=[]  stderr_empty=True
termux_verify.py               exit=0  status=clean  verification_shaped=1  rules=[]  stderr_empty=True
test_egr2_integration.py       exit=0  status=clean  verification_shaped=1  rules=[]  stderr_empty=True
test_termux_verify.py          exit=0  status=clean  verification_shaped=1  rules=[]  stderr_empty=True
test_verified_aggregate.py     exit=0  status=clean  verification_shaped=1  rules=[]  stderr_empty=True
```

The six-versus-seven `verification_shaped` count is expected: `noise_probe.py`
scans cleanly but is not classified as verification-shaped by the filename or
entry-point heuristic. A clean scan is not a correctness proof for the EGRR
scripts, their scientific claims, or the Vacuity detector.

## Self-tests and regression tests

### Embedded scanner self-test

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 "$VENV/bin/python" "$REPO/vacuity_lint.py" --selftest
```

Result: **20/20 checks passed**, process exit `0`, stderr empty. The self-test
includes the documented unreachable-failure blind spot as P12.

### Repository regression suite

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 "$VENV/bin/python" -m unittest discover -s tests -v
```

Result:

```text
Ran 24 tests in 0.522s

OK
```

Process exit status: `0`. The suite covers exit classification, JSON metadata,
empty scans, suppression behavior, syntax errors, entry-point detection and
version behavior. It does not prove semantic test quality or reachability.

### Installed release contract

The repository’s `release_smoke.py` contains 13 installed-CLI checks. Running
it directly from the repository directory is contaminated by the pre-existing
empty untracked `vacuity_lint.egg-info/` directory, which makes
`importlib.metadata.version()` resolve `None` in that working-directory
context. No repository artifact was removed to work around this.

The same unmodified script was executed from the isolated evidence directory
via `runpy`, with the v2.0.0 installed console command on `PATH`:

```bash
PATH="$VENV/bin:$PATH" REPO="$REPO" PYTHONDONTWRITEBYTECODE=1 "$VENV/bin/python" - <<'PY'
import os
import runpy
runpy.run_path(os.path.join(os.environ["REPO"], "release_smoke.py"), run_name="__main__")
PY
```

Result: **RELEASE CONTRACT: PASS (v2.0.0, 13 checks)**, process exit `0`.
The 13 checks covered installed executable/metadata, embedded self-tests,
clean/defective/empty scans, syntax findings, version output, JSON finding
metadata, and empty-scan JSON exit semantics.

### Companion self-tests

Commands:

```bash
PYTHONDONTWRITEBYTECODE=1 "$VENV/bin/python" "$REPO/mutation_probe.py" --selftest
PYTHONDONTWRITEBYTECODE=1 "$VENV/bin/python" "$REPO/provenance_audit.py" --selftest
```

Both exited `0`. The mutation probe observed and reported KILLED, SURVIVED and
CRASHED outcomes, excluding crash mutants from the score. The provenance audit
observed reconstructible and not-reconstructible cases and rejected authorship
inference from coding style.

## Reproduction commands and path variables

For an independent rerun from this workspace, define:

```bash
EVAL_ROOT="<ORIGINAL_EVALUATION_WORKSPACE>"
REPO="$EVAL_ROOT/repo"
CASES="$EVAL_ROOT/independent_cases"
EVIDENCE="$EVAL_ROOT/independent_evidence"
VENV="$EVAL_ROOT/venv"
```

The exact command transcript, including the full three-case stdout/stderr
blocks and the recorded test results, is in `commands_and_results.txt`.
Environment and version details are in `environment_versions.txt`.

## Evidence completeness and limitations

### Complete for this requested scope

- Evaluated commit, release tag distinction, package version, OS, Python and
  source hash are recorded.
- Original 16-case fixture set was recovered and rerun; result was 16/16.
- Seven EGRR copies were recovered, source/copy hashes matched, and all seven
  were rescanned cleanly.
- All three requested findings were reproduced with minimal local fixtures,
  exact commands, stdout/stderr, exit status and technical classification.
- Embedded, repository, installed-release, mutation and provenance checks were
  executed where the isolated environment supported them.
- No upstream source was modified and no external action was taken.

### Remaining gaps

1. The original evaluation’s standalone raw JSON scan manifest was not found;
   the seven-file scan was rerun and its fresh output is recorded here.
2. The live evaluation workspace is under `<ORIGINAL_TEMPORARY_WORKSPACE>` and is temporary.
   This package is local and should be copied to a durable private location if
   it must survive system cleanup; copying it elsewhere was not requested here.
3. The isolated venv does not contain pytest. The empty-function pytest control
   used the host `/usr/local/bin/python3` with pytest 9.1.1; the scanner itself
   was still tested with the isolated venv Python 3.14.5.
4. The current `main` commit is post-release. Results should not be silently
   relabeled as evidence for the tag commit alone.
5. A clean Vacuity scan of the seven EGRR scripts does not prove that those
   scripts are correct, reachable, scientifically valid, or secure.
6. The three reproduced findings do not establish overall precision/recall or
   security coverage. They are bounded examples of documented heuristic
   behavior and limitations.

## Maintainer-facing conclusion

The package provides a reproducible, local verification record for Chad Holland:

- the v2.0.0 scanner and current post-release `main` are identified exactly;
- the previous 16 constructed cases and seven EGRR scan inputs are recovered and
  re-executed;
- VL002’s docstring behavior is a confirmed heuristic false positive;
- assertion-free pytest functions and unreachable failure branches are confirmed
  documented limitations;
- the tool’s own 20-check self-test, 24 regression tests, 13 installed-release
  contract checks, mutation self-test and provenance self-test passed in their
  respective scopes.

These results support further maintainer discussion and reproducibility review.
They do not constitute a claim that Vacuity Lint is correct in general, that
the scanned EGRR scripts are correct, or that any security property has been
validated.

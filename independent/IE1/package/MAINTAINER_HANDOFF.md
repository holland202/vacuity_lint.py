# Vacuity Lint v2.0.0 — maintainer evidence handoff

**Evaluator:** Putluru Sandeep (`sunny-kavixo`) · **Prepared:** 2026-10-18  
**Status:** Local draft for approval; nothing submitted externally.

## Scope and provenance

This continues the existing independent evaluation. **No completed scanner,
pytest, self-test or regression run was repeated for this handoff.** Observed
results below are from the retained 2026-10-18 reproduction record; this step
performed backup, hash comparisons, pinned-source verification and a read-only
GitHub issue check. Historical evidence is supplied as labeled sanitized copies under
`independent_evidence/`; this report supplies portable instructions and corrects
the earlier interpretation of VL002. Source snapshots retain upstream licenses.

### Exact instrument and environment

| Item | Evaluated value |
|---|---|
| Repository | <https://github.com/holland202/vacuity_lint.py> |
| Source commit | `da5fe76ddcd660c2d21a89853623e905a0b33708` (`main` when evaluated) |
| CLI/source version | `2.0.0` |
| Release tag commit | `v2.0.0` → `c31330e8baaf44ef6610b26272c0ab8910e610be` |
| Scanner SHA-256 | `3cb0d07d4d5b807132a6a82bef50e09051d4fab35e00449e4cf435745a406971` |
| OS | macOS 27.0.1, build 26A434, arm64 |
| Scanner Python | Python 3.14.5, existing evaluation venv |
| Pytest control | Host Python 3.14.5 with pytest 9.1.1 |

The evaluated commit is one commit after the release tag; the only tracked
change between them is `.github/workflows/release-check.yml`. Results are pinned
to the full evaluated SHA, not to whichever revision `main` points to later.
Pytest was not installed in the evaluation venv; the pytest outcome is a separate
host-interpreter control, not part of Vacuity Lint's execution.

## Start here — no original research checkout needed

The distribution contains 19 selected upstream files at the evaluated commit,
including the scanner, rule reference, regression tests and licenses; the 16
constructed cases and their original driver; and all seven static EGRR inputs.
There is no copied `.git` configuration, venv, credential, or private session log.

Open a terminal **in this package's root folder**. All following paths are
relative to it and work after moving the complete folder to another machine:

```bash
shasum -a 256 -c SHA256SUMS
python3 -B verify_package.py
python3 --version
python3 -B source_snapshot/vacuity_lint.py --version
python3 -m pytest --version
```

The scanner needs only Python 3.10+ and the standard library; no installation is
required. Only the pytest control needs pytest (recorded version: 9.1.1). If
unavailable, use a separate environment with `pytest==9.1.1`; do not confuse a
missing pytest dependency with a scanner result. No dependency was installed
for this handoff. Do not run pytest across the whole package: one constructed
fixture is intentionally invalid Python and the copied EGRR files are scan
inputs, not a self-contained runnable EGRR test suite.

The commands below are intended to be run individually, **not in a shell that
stops on the expected scanner exit 1**. `printf` records the immediately preceding
process status. Paths in retained output point at the old workspace; rerunning
with these commands changes only the displayed file path, not the input bytes.

## A. VL002 docstring diagnostic — independently reproduced

File: `independent_evidence/reproductions/vl002_docstring.py`

```python
"""Documentation mentions a [FAIL] result, but this is a clean demo."""

if __name__ == "__main__":
    print("documentation loaded")
```

```bash
python3 -B source_snapshot/vacuity_lint.py independent_evidence/reproductions/vl002_docstring.py
printf 'scanner_exit=%s\n' "$?"
python3 -B independent_evidence/reproductions/vl002_docstring.py
printf 'target_exit=%s\n' "$?"
```

- **Semantic expectation:** the target emits no failure message; `[FAIL]` is
  documentation only. This is a false positive if interpreted as an emitted
  failure report.
- **Documented scanner expectation:** VL002, exit **1**. At this exact commit,
  `RULES.md:20–27,40` expressly counts all AST string constants, including
  docstrings; it says the name is historical and the string need not be printed.
- **Observed scanner:** one verification-shaped file, one
  `PRINTS_FAIL_ONLY`/VL002 diagnostic, exit **1**, stderr empty. Diagnostic:
  `prints failure text 1x but has no assert, raise, or nonzero exit`.
- **Observed target execution:** stdout `documentation loaded\n`, stderr empty,
  exit **0**. No failure text is emitted.

`visit_Constant()` counts the docstring's `[FAIL]` token. This is **documented
heuristic behavior with misleading emitted-message wording**, not a demonstrated
violation of the rule contract. The earlier report called it an implementation
bug and incorrectly described the filename as `verify`-shaped; its failure
string is the relevant selection signal. Those original statements are retained
for provenance, but this qualification supersedes them. Improving the diagnostic
wording, or optionally distinguishing docstrings from actual output calls, is a
proposal rather than an implemented fix.

## B. Empty pytest test — scanner and pytest are separate observations

File: `independent_evidence/reproductions/empty_pytest.py`

```python
def test_empty():
    pass
```

```bash
python3 -B source_snapshot/vacuity_lint.py independent_evidence/reproductions/empty_pytest.py
printf 'scanner_exit=%s\n' "$?"
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider independent_evidence/reproductions/empty_pytest.py
printf 'pytest_exit=%s\n' "$?"
```

- **Expected scanner:** no finding, exit **0**, under the current rule that a
  `def test_*` declaration is itself a recognized potential failure path.
- **Observed scanner:** one verification-shaped file, zero findings,
  `no vacuous verification found`, exit **0**, stderr empty.
- **Expected pytest:** collect and run the explicitly selected test file;
  its `pass` body returns normally.
- **Observed pytest:** `1 passed in 0.00s`, exit **0**, stderr empty. This is a
  pytest result, **not** a Vacuity Lint assertion about test quality.

This fixture verifies nothing meaningful. It demonstrates a **syntactic-scope
limitation**, not a new claim that pytest or the scanner violates its documented
contract. It differs from `defective/test_empty.py`, which has **no test
function** and correctly produces VL001/VL003.

## C. Unreachable failure-path control — previously documented

File: `independent_evidence/reproductions/verify_unreachable_raise.py`

```python
if __name__ == "__main__":
    if False:
        raise RuntimeError("unreachable")
    print("success")
```

```bash
python3 -B source_snapshot/vacuity_lint.py independent_evidence/reproductions/verify_unreachable_raise.py
printf 'scanner_exit=%s\n' "$?"
python3 -B independent_evidence/reproductions/verify_unreachable_raise.py
printf 'target_exit=%s\n' "$?"
```

**Expected and observed:** scanner sees one verification-shaped file, returns
zero findings/exit **0**, stderr empty. Executing the target prints `success\n`,
stderr empty, exit **0**. The `raise` under `if False` cannot execute. This
independently reproduces the already documented Type-B reachability limitation
(`README.md:162–180`, `RULES.md:45–51,87–94`); **not a newly discovered bug**.

## Existing issue overlap — checked 2026-10-18

All open/closed GitHub issues returned by `gh issue list --state all --limit
100` were read; the only returned issue was
[#7](https://github.com/holland202/vacuity_lint.py/issues/7), open with no
comments at this check. Snapshot: `provenance/github_issues_snapshot.json`.

- **VL002/docstrings:** #7 finding 3 covers a different bug: raw-source
  suppression markers inside strings/docstrings can hide findings. It shares
  a documentation-versus-executable-text theme but is **not** this VL002
  failure-word counting example. The VL002 example is already anticipated by
  `RULES.md`; no claim of novelty or an undisclosed issue is made.
- **Empty pytest test:** not separately raised in #7's numbered findings.
  Related known misses exist in upstream `E16/RESULTS.md:14–21` (skipped test
  and weakened assertion), and `RULES.md` counts `test_*` declarations as fail
  paths. This is a related scope boundary, not an exact duplicate of those
  fixtures. Upstream E16 results are maintainer-authored context, not my results.
- **Unreachable path:** expressly documented in the README/rule reference and
  self-test P12, so no new issue is proposed for that control.

This is a bounded public-issue check, not proof that no private discussion or
unindexed historical duplicate exists. None of #7's other findings were rerun
or adopted as independently observed findings in this handoff.

## Seven EGRR scripts — retained static scan results

All inputs are bundled in `independent_cases/egrr_copies/`. **Scan only; do not
execute them.** Their imports/runtime dependencies are not needed for AST scans.
No access to the original Principia checkout is required.

| File | Retained scanner exit | Findings | Verification-shaped |
|---|---:|---:|---:|
| `descriptive_reporting_gate.py` | 0 | 0 | 1 |
| `noise_probe.py` | 0 | 0 | 0 |
| `registered_fixture_gate.py` | 0 | 0 | 1 |
| `termux_verify.py` | 0 | 0 | 1 |
| `test_egr2_integration.py` | 0 | 0 | 1 |
| `test_termux_verify.py` | 0 | 0 | 1 |
| `test_verified_aggregate.py` | 0 | 0 | 1 |

Retained directory scan: **7 files**, **6 verification-shaped**, zero findings,
zero suppressions, `status=clean`, exit **0**, stderr empty. `noise_probe.py`
does not match the selection heuristic; it is not evidence of test coverage.

One historical copy (`descriptive_reporting_gate.py`) was absent when preparing
this backup. It was recovered read-only from public Principia commit
`52915857c8bddee66cf86d48c5c8cbc5807168a5`, path
`experiments/egrr_issue28/descriptive_reporting_gate.py`. Its SHA-256 exactly
matches the previously recorded scan input:
`5492a13d6ddb75e73e95f83c7e848174797d43af27ce5bf703b4e436c6c1a526`.
See `provenance/recovered_egrr_input.json`. **No scan was rerun on the recovered
file in this step**; the table reports the retained observations.

Optional reproduction from the package root (not repeated for handoff):

```bash
python3 -B source_snapshot/vacuity_lint.py --format json independent_cases/egrr_copies
printf 'scanner_exit=%s\n' "$?"
```

To reproduce each row, use that command with the full relative path of a single
bundled input in place of the directory. Clean scans do **not** prove EGRR
correctness, scientific validity, reachable assertions, security or Vacuity
Lint precision/recall. This package does not authorize or perform EGRR study runs.

Exact optional per-file and 16-case commands (not repeated for handoff):

```bash
for file in independent_cases/egrr_copies/*.py; do
  python3 -B source_snapshot/vacuity_lint.py --format json "$file"
  printf 'scanner_exit=%s\n' "$?"
done
PYTHONDONTWRITEBYTECODE=1 python3 independent_cases/run_independent.py source_snapshot/vacuity_lint.py independent_cases
printf 'driver_exit=%s\n' "$?"
```

The retained driver result was `independent_cases=16 failures=0`, exit **0**.

## Prior validation, backup verification and limits

**Retained prior observations, not rerun:** 20/20 embedded checks; 24 repository
regressions; 13 installed-release checks; mutation and provenance self-tests
passed; 16/16 expected black-box classifications matched. These include known
misses/false positives as expected classifications, not 16 correct detections.
The earlier direct installed-release run failed because of empty local package
metadata; an unmodified-script `runpy` invocation passed. Both are preserved.

**Original-backup checks:** all 82 original manifest entries passed before ZIP
packaging. The original backup's 42 source files had been verified against
the pinned Git blobs. This distribution retains an unmodified source subset
and all input fixtures, with sanitized historical documents and a new
manifest. See `DISTRIBUTION_NOTES.md`, `provenance/distribution_inventory.json`
and `SHA256SUMS`. Verify from the extracted root with
`shasum -a 256 -c SHA256SUMS` and `python3 -B verify_package.py`.

Package map:

- `MAINTAINER_HANDOFF.md`: current concise interpretation and portable commands.
- `independent_evidence/`: sanitized historical report and command/result record,
  environment file and three minimal reproductions.
- `independent_cases/`: 16 original constructed fixtures, driver, seven static
  EGRR inputs and the preserved empty directory.
- `source_snapshot/`: selected unmodified pinned upstream files and licenses; not a full checkout.
- `provenance/`: sanitized distribution inventory, recovery record and public issue snapshot.

The previous `commands_and_results.txt` is an assembled transcript, not a full
set of separate raw stdout/stderr captures. In particular, it labels unittest
stderr empty although unittest normally reports to stderr; only the retained
24-test result summary is relied on here. A standalone raw manifest from the
earliest seven-script scan was not found. Historical paths and old
interpretations remain in labeled historical documents with private paths
redacted; this report's relative commands and qualifications are authoritative.

No virtual environment, private log/database, model, or unrelated research tree
is needed. No upstream/research files were edited, no scientific experiment was
performed, and no issue, PR, commit, push or external handoff was submitted.
**Next action requires Sandeep's approval of the proposed message and channel.**

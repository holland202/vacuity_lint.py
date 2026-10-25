# IE1-B: an empty `test_*` function, registered before any code

**State:** REGISTERED, NOT RUN. No scanner code, test, fixture or selection file exists at the commit that adds this
file. No real test suite has been cloned or looked at.
**Origin:** IE1 (Putluru Sandeep, 2026-10-18) found that `def test_empty(): pass` scans clean. The 2026-10-25 rerun
([IE1 addendum](../independent/IE1/README.md#addendum-2026-10-25-rerun-on-main-after-prs-12-and-13)) shows it is
still clean on `main` `79cbff3` whenever pytest would collect the file. Proposal: [IE1/PROPOSALS.md](../independent/IE1/PROPOSALS.md#ie1-b-an-empty-test-function).
**Instrument:** `vacuity_lint.py` at `main` `79cbff3` (2.0.1.dev0). This does **not** touch the E15 pin (`e549dbf…`).
**Authors:** Claude (Anthropic, Opus 5.5), at Chad Holland's direction (2026-10-25). Human review level: direction
only. Everything run under this registration will be **self-tested**.

## Two owner decisions are needed before any code

- **D1. IE1's frozen expectation.** Sandeep's runner expects `blind/test_empty_function.py` to scan clean, and CI runs
  that runner. Fixing IE1-B must flip that case. VL-FP-001 withdrew its `assert True` fix (V-B) for the same reason:
  changing his expectations would rewrite someone else's record. Proposed mechanism, which also unblocks V-B later:
  - his package and runner stay byte-identical;
  - a new `ci/run_ie1.py` runs his runner unchanged and reads `ci/ie1_divergences.json`;
  - each entry names one case, the registration that changes it, his recorded expectation, and the new expectation;
  - the wrapper passes only if every FAIL line is a listed case **and** its actual output equals the new expectation
    exactly;
  - a listed case that still matches his original expectation also fails CI, so a divergence cannot go stale.

  If the owner rejects D1, IE1-B is not implemented and stays a documented blind spot.
- **D2. The narrow design below.** It flags less than the proposal allowed. Widening it needs a new registration.

## Design (settled here, not after a run)

New rule **VL006 `EMPTY_TEST`**, category `heuristic`, severity `warning`. It is a finding, so exit 1. The existing
suppression marker applies to it.

**Which functions.** These are the test functions pytest or unittest would collect:
- a module-level `def` or `async def` named `test_*` in a file pytest collects by default (`test_*.py`, `*_test.py`);
- a `test_*` method of a class named `Test*` in such a file;
- a `test_*` method of a class whose base name ends in `TestCase`, in any file.

Nested functions are not collected, so they are out of scope.

**Empty body.** After an optional leading docstring, every statement is `pass`, `...`, bare `return` or
`return None`. A docstring-only body is empty. Any other statement means the body is not empty, including an
assignment, a call or any other expression, because it might raise.

**Not flagged even with an empty body:**
- **(a) Parameters.** The function takes any parameter other than `self` or `cls`. A pytest fixture can fail, so the
  test can fail.
- **(b) Fixture decorator.** It carries a `usefixtures` decorator, for the same reason.
- **(c) Skip decorator.** It carries a decorator whose final attribute is `skip`, `skipif`, `skipIf` or `skipUnless`.
  A skipped test does not pass. `xfail` is **not** excluded: a non-strict empty `xfail` test passes as XPASS.

**File-level classifications do not change.** An empty `test_*` still counts in the file's fail-path inventory, so
VL001 through VL005 give the same result on every file as at `79cbff3`. VL006 is only ever added.

## Fixtures (written after this commit, before any code)

These fixtures must be flagged, with VL006 and exit 1:
- **E1** `def test_x(): pass` in `test_a.py`;
- **E2** a body of `...`;
- **E3** a docstring-only body;
- **E4** a body of bare `return`;
- **E5** `async def test_x(): pass`;
- **E6** `def test_x(self): pass` in `class TestFoo` in `test_a.py`;
- **E7** `def test_x(self): pass` in `class Foo(unittest.TestCase)` in `verify_b.py`, which calls `unittest.main()`;
- **E8** a non-strict `@pytest.mark.xfail` empty test;
- **E9** IE1 `blind/test_empty_function.py`, as a copy;
- **E10** IE1 `reproductions/empty_pytest.py`, copied as `test_empty_pytest.py`.

These fixtures must stay clean:
- **G1** IE1 `clean/test_real.py`;
- **G2** a body of `x = compute()` only;
- **G3** a body that calls a helper, `check()`;
- **G4** `@pytest.mark.skip` on an empty test;
- **G5** `@unittest.skip("…")` on an empty `TestCase` method;
- **G6** `def test_x(db): pass`, where the fixture parameter can fail;
- **G7** `@pytest.mark.usefixtures("db")` on an empty test;
- **G8** `def helper(): pass` in `test_a.py`, which is not a test;
- **G9** a nested `def test_inner(): pass` inside a test function;
- **G10** an empty `test_*` method in a class not named `Test*` and not a `TestCase`, in `test_a.py`.

## Predictions

- **B1 (before the fix).** The new test file fails on `79cbff3`: E1 to E10 each scan without VL006.
- **B2 (after the fix).** E1 to E10 each produce VL006 and exit 1.
- **B3 (no new false positives on fixtures).** G1 to G10 produce no VL006. Their other rule IDs equal those at
  `79cbff3`.
- **B4 (no regressions).** All of these still pass:
  - `--selftest`;
  - `python3 -m unittest discover -s tests`;
  - `ci/check_issue7_mutants.py`, `ci/verify_gate.py` and `ci/verify_fixtures.py`;
  - E16's runner;
  - the IE1 runner through the D1 wrapper, with exactly **one** listed divergence: E9's source case,
    `blind/test_empty_function.py`, now `exit=1, rules=['VL006']`.
- **B5 (anti-vacuity).** Two checks:
  - removing the VL006 check makes the B2 tests fail;
  - a self-scan of this repository, with E16 fixtures, IE1's package and the new fixtures excluded as in `gate.yml`,
    reports **zero** VL006, so the rule can return nothing.
- **B6 (real suites; data used to judge, not to design).** The design above was fixed without looking at any of
  these suites.
  - **Scope.** The `tests/` directory of `pallets/click`, `pallets/flask`, `psf/requests`, `python-attrs/attrs` and
    `encode/httpx`.
  - **Pinning.** Each is pinned to its default-branch HEAD SHA, recorded in `IE1B/selection.txt` and committed
    **before** any scan.
  - **Exclusion.** `pytest-dev/pytest` is excluded in advance, because its own tests deliberately plant empty tests
    as fixtures for the framework.
  - **B6a.** VL006 fires **at most 10** times across the five suites. More than that means the rule is too noisy to
    gate on, and that result is reported, not tuned away.
  - **B6b.** Every hit is hand-classified, and the categories are reported with counts. The categories are:
    placeholder or TODO; deliberate smoke/collection test; other. No hit may fall under exclusions (a) to (c). One
    that does is an implementation defect.

A refuted prediction is kept and explained. It is not edited away.

## Left unrun by design

Whether a test whose body only calls helpers that cannot fail should count as empty. That needs interprocedural
analysis and a separate registration.

## Provenance

Claude (Anthropic, Opus 5.5) wrote this registration from Putluru Sandeep's IE1 finding and the 2026-10-25 rerun →
human validation: not performed → human editing/curation: direction by Chad Holland (2026-10-25) → human
responsibility: Chad Holland. Human review level: direction only.

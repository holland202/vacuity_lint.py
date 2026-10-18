<p align="center">
  <img src="assets/vacuity-lint-mark.svg" alt="Vacuity Lint: a checkmark under inspection" width="112">
</p>

# vacuity-lint

> **Release and license history:** [GitHub Releases](https://github.com/holland202/vacuity_lint.py/releases) include historical MIT versions `v1.0.0` (`6ee0671`) and `v1.1.0` (`92e1ced`), preserved in [ARCHIVED_RELEASES.md](ARCHIVED_RELEASES.md). **v2.0.0** changes to BSL 1.1; the source tree version does not itself prove a `v2.0.0` tag or GitHub Release has been published. See [RELEASE_2_0_0.md](RELEASE_2_0_0.md) for acceptance and publication status. Python 3.10+ is supported. PyPI publication has not been verified.

## Install and try it

Python 3.10+; **no third-party runtime dependencies**. To install directly
from a checkout of this repository:

```sh
python3 -m pip install .
vacuity-lint --selftest
vacuity-lint ./your-python-project
```

The tool returns **0** when scanned Python files have no detected findings,
**1** when it reports findings, and **2** when there were no Python files to
scan. It does not run code under inspection or contact a remote service.

## JSON diagnostics (v1.1.0)

Use the **same scanner and exit codes** with machine-readable output:

```sh
vacuity-lint --version
vacuity-lint ./your-python-project --format json
```

The JSON includes file counts, an array of findings with stable rule IDs
(e.g. `VL002` for `PRINTS_FAIL_ONLY`), severity/category labels,
and reason-bearing intentional suppressions. It does **not** fabricate a
line number for its file-level findings. JSON output is also provided for
empty scans, which still exit **2**.

Use [RULES.md](RULES.md) for precise triggers, examples, rule metadata and
limitations. CI can enforce the existing code `1`, or capture and review it
as an advisory report; the tool does not provide a configurable
`--fail-on` override in this release. An `UNPARSEABLE` finding means
analysis was incomplete and is categorized separately from heuristic warnings.

A tiny demonstration:

```sh
mkdir -p demo
printf "print('[FAIL] verification failed')\n" > demo/verify_checks.py
vacuity-lint demo
echo $?
```

Expected: the scanner identifies a verification-shaped file that prints
failure without a recognized failing exit path; exit code **1**. The finding
is a heuristic *review prompt*, not proof that the code is unsafe.

This detector intentionally **does not** prove tests are correct, detect
all logically unreachable failure branches, or replace mutation testing.
See [RELEASE.md](RELEASE.md) for release acceptance and [LICENSE](LICENSE) for
reuse terms.


Finds verification code that cannot fail.

A test suite that always passes, a `verify_*.py` that prints
`MATH IS WRONG - STOP` and then exits 0, a `test_*.py` containing no test
functions — these report success to whatever calls them regardless of what
they discover. CI goes green. A `make` target succeeds. Nobody finds out.

`vacuity_lint.py` is a single file, AST-based, zero dependencies. It exits
with three exit codes, so a caller can tell looking from finding: **0**
looked and found nothing, **1** looked and found something, **2** could not
look. The third exists because an earlier version, run on a tree with no
Python files, printed a clean bill of health for a tree it never read.

```
python3 vacuity_lint.py .            # scan a tree
python3 vacuity_lint.py --selftest   # 20 checks, exit 1 on any failure
```

Example output:

```
python files scanned    : 19          verification-shaped     : 5
findings                : 1           declared intentional    : 1

  [intentional] ./tests/test_governance_loop.py
      reads live device temperature via ThermalMonitor, so its verdict
      depends on how warm the phone is; deliberately excluded from
      run_all_tests.py

PRINTS_FAIL_ONLY  (1)
  ./calibrate_thermal.py   prints failure text 1x but has no assert,
                           raise, or nonzero exit
```

## Also in this repository

`vacuity_lint.py` is one of four artifacts here. The other three exist
because the first one is not enough.

| | |
|---|---|
| `vacuity_lint.py` | Finds gates with no fail path. Static, AST-based. |
| `mutation_probe.py` | Asks the question the linter cannot: does the verdict actually *depend* on the logic it claims to check? Mutates the target and reports KILLED, SURVIVED, or CRASHED. A mutant that makes the target die to an uncaught exception has not been *detected* by it, so CRASHED is excluded from both sides of the score. |
| `provenance_audit.py` | Measures whether a repository can say who wrote its verification code, under a five-tier evidence hierarchy frozen in code. Tier 5, "inferred from coding style", is inadmissible by construction, so the measurement cannot become circular. A low score is a result, not a build failure, so it exits 0 either way. |
| `E15/PREREG.md` | A preregistration, committed before the experiment it describes was run. Registers a three-arm prevalence measurement and pins this tool at `e549dbf` for the duration. Status: REGISTERED, NOT RUN. |

Each of the three tools ships a self-test that proves it can return **more than one
verdict**, under fixtures that force each answer in turn. A detector stuck on one answer is the defect this repository exists
to find, and that applies to these tools first.

## A third category, found 2026-09-11

The taxonomy below splits vacuity into Type A (no fail path) and Type B (a
fail path that cannot fire). A third kind turned up in another repository,
and `vacuity_lint.py` is blind to it by definition:

**a gate whose verdict is redrawn on every run.**

An assertion required that an estimator win at least 40 of 100 trials, and
drew those 100 trials from an unseeded generator. CI had passed it 45 times.
Measured over 60 executions of identical code, the statistic ranged 31 to 62
and fell below the threshold twice. This tool had scanned that repository and
reported it clean, correctly by its own definition: the assert was present,
it could raise, the exit code was wired. It was simply not asking the same
question twice.

Not yet detected here. Recorded because an undetected category is worth more
in the README than in a notebook.

## Why this exists

On 2026-07-26 four independent codebases were found to contain a verification
construct that could not fail. Different authors, different AI models, written
in different months. Nobody had noticed, because the failure path in each had
never been taken — so nobody discovered it could not be reported.

That is the whole mechanism. **A gate you have never seen fail is not evidence
that anything passed.**

Two months later the same defect turned up again in a second copy of a file
that had already been fixed elsewhere. Fixing a file does not fix its copies.

## What it detects

| Finding | Meaning |
|---|---|
| `NO_FAIL_PATH` | Verification-shaped and runnable, but contains no `assert`, no `raise`, no non-zero exit, and no `def test_` |
| `PRINTS_FAIL_ONLY` | Prints failure text ("FAIL", "ERROR", "WRONG") while having no fail path — announces the problem, reports success |
| `UNCOLLECTABLE_TEST` | Named `test_*.py` but declares no test functions. Run alone, pytest collects nothing and exits 5; inside a larger suite the run stays green while this file contributes no tests |
| `ALWAYS_EXITS_ZERO` | Every exit in the file is `exit(0)` |
| `UNPARSEABLE` | Did not parse — reported, never silently skipped |

A file counts as **verification-shaped** only if it both looks like a check
(by name, or by declaring `def test_`) *and* is actually runnable — it has a
`__main__` guard, a module-level call, or test functions. Library modules that
merely happen to be called `something_gate.py` are not tests and are not
flagged.

## What it does NOT detect — measured, not estimated

The original four defects split into two kinds:

- **Type A — no fail path exists.** Statically detectable. This tool finds these.
- **Type B — a fail path exists but cannot fire.** A marker that is defined but
  never written; a boolean branch that is dead because one condition implies
  another. Needs reachability analysis.

The four split exactly 2 / 2, and **this tool caught 2 of 4**: both Type A
cases and neither Type B case. That is four cases, not a detection rate — and
Type B is the harder half.

Do not describe this as catching the pattern. It catches half of it. The blind
spot is encoded as selftest **P12**, so it is a documented property rather than
an omission:

```
[PASS] P12 documented blind spot: unreachable fail path not caught
```

## The suppression marker, and why it works the way it does

Some flagged files are deliberate. A test that reads live hardware temperature
has a machine-dependent verdict and may be excluded from a suite on purpose.
The tool cannot know that, so it would re-report it forever.

```python
# vacuity-lint: intentional - reads live device temperature, so the verdict
# depends on ambient conditions; excluded from run_all_tests.py
```

**A bare marker with no stated reason does not suppress anything.** That is
selftest P16, and it is the point of the design: the mechanism forces the
justification into the file instead of handing you a mute button. Suppressed
cases are printed under *declared intentional* with their reason attached, so
they stay visible and the open count can converge to zero honestly.

## Self-test

20 checks. Run them before trusting a single finding.

```
P1  test_*.py with no test funcs -> UNCOLLECTABLE_TEST
P2  prints FAIL, no fail path -> PRINTS_FAIL_ONLY
P3  verification shape, exit 0 only -> flagged
P4  real pytest test -> no finding
P5  conditional nonzero exit -> no finding
P6  dynamic exit expression -> no finding
P7  ordinary module is not verification -> no finding
P8  assert counts as a fail path -> no finding
P9  clean tree yields zero findings (tool can find nothing)
P10 defective tree yields findings (tool can find something)
P11 syntax error reported, not silently skipped
P12 documented blind spot: unreachable fail path not caught
P13 library module named *_gate.py, no __main__ -> no finding
P14 test_*.py that exits nonzero is not UNCOLLECTABLE
P15 marker WITH a reason suppresses the finding
P16 bare marker with NO reason does NOT suppress
P17 suppression is recorded, not silent
P18 suppression in one file does not affect another
P19 tree with no python files -> exit 2, not a clean bill
P20 tree with a clean python file -> still exit 0

20/20 checks passed
```

P9/P10 and P19/P20 are the two anti-vacuity pairs, and they are not decoration: a detector
must be shown capable of returning *nothing* on a clean tree and *something* on
a defective one. Without both, this tool would be an instance of the defect it
looks for.

## Measurements

Run across 13 repositories belonging to one author. Every number below was
produced by this tool; each stage is reported because the corrections matter
more than the final figure.

| Stage | Findings | Note |
|---|---:|---|
| First pass | 21 | across 6 of 13 repos |
| After precision fixes | 13 | a 38% cut — see below |
| Counted as distinct files | 12 files | one file produced two findings |

**Two precision bugs, found by hand-checking rather than by the tool.** Of the
7 findings in one repository, 5 were false positives. Cause (a): library
modules matched on filename alone, so `*_gate.py` modules were judged as tests
— fixed by requiring executability. Cause (b): `UNCOLLECTABLE_TEST` fired on
runnable scripts that correctly exit non-zero — now suppressed when a fail path
exists. Both true positives survived the tightening. P13 and P14 are the
regression guards.

**Two predictions were registered before running, and both were refuted:**

1. "Findings in at least half the repos" → 6 of 13 (46%). Refuted, narrowly.
2. "Under 10 findings total after the fixes" → 13. Refuted.

Both are kept. They are the reason the numbers above are worth anything.

A separate clean-room reimplementation was later written to compare this
author's repositories against ten popular human-authored ones. **Its numbers
are not comparable to the figures above** — different instrument, different
thresholds — and it is not distributed here. The one durable result from that
experiment is worth stating anyway: the interesting difference was not the
finding *rate* but the *denominator*. The control repositories averaged 34.7
verification-shaped files each; these averaged 1.2. The problem was mostly not
that gates failed, but that there were almost none to fail.

## Suggested use

As a pre-commit step. The strongest argument for it: the tool flagged a file
that two people had committed the previous day, on a day they had spent fixing
three other instances of exactly this defect. Knowing about the pattern is not
sufficient protection against it.

```
vacuity-lint .              # or, without installing: python3 vacuity_lint.py .
```

Exit code 1 on findings is what blocks the commit or CI step. In a script
with several commands, keep that code: `vacuity-lint . || exit "$?"`.

Do not append `|| echo "..."`. A successful `echo` turns the scanner's 1 back
into 0, so the step passes while printing a warning — the exact defect this
tool looks for. This repository's own CI made that mistake until 2026-08-14
(see the comment in `.github/workflows/gate.yml`).

*Corrected 2026-10-16:* this section previously recommended
`python3 vacuity_lint.py . || echo "verification that cannot fail - fix or mark intentional"`.
On a tree the scanner flags (exit 1), that command exits 0.

## Limitations

- Python only.
- Static analysis. Nothing is executed, so a fail path that exists but is
  unreachable is not caught — see P12.
- Heuristic notion of "verification-shaped". A check named in a way the
  heuristic does not recognise will be missed.
- Filenames matter to it, which means unusual project layouts may need the
  suppression marker more than tidy ones.
- A `test_*` function whose body cannot fail (`def test_x(): pass`) is not
  flagged: declaring a test function counts as a fail path. Found by IE1.
- One human maintainer (Chad Holland). One independent evaluation so far:
  IE1, by Putluru Sandeep (2026-10-18), on 2.0.0 with cases he wrote. It
  found the tool behaving as documented, including the blind spots above,
  and a misleading VL002 message (`independent/IE1/`). That is one outside
  evaluation, not a validation. AI systems
  contributed code, tests and documentation; where recorded, they are named
  in commit trailers (Claude, Anthropic). CI runs the self-tests and a
  planted-defect probe on every push (`.github/workflows/gate.yml`). Judge
  accordingly.

## Contributing

The useful contribution is a **false positive or a false negative**, with the
smallest file that reproduces it. Type B detection — reachability analysis for
fail paths that exist but cannot fire — is the open problem and the half this
tool does not solve.

## License

**Vacuity Lint v2.0.0 and later: [Business Source License 1.1](LICENSE).** Non-production testing, evaluation, research, and security review are free; defined individual, nonprofit, academic, and qualifying small-organization production uses are also permitted. Other production uses require a separate commercial license. See [COMMERCIAL.md](COMMERCIAL.md) for the summary and LICENSE for controlling terms. Each BSL-covered version converts to Apache-2.0 four years after that version's first publication.

**v1.1.0 and earlier: MIT.** Historical release tags and archives remain unchanged under their original [MIT license](LICENSE-MIT). See [ARCHIVED_RELEASES.md](ARCHIVED_RELEASES.md).

*Vincit Omnia Veritas.*

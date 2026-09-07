# vacuity-lint

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
| `UNCOLLECTABLE_TEST` | Named `test_*.py` but declares no test functions, so pytest collects nothing and reports green |
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

The four split exactly 2 / 2, and **this tool caught 2 of 4.** It finds every
Type A case and misses every Type B case — and Type B is the harder half.

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
python3 vacuity_lint.py . || echo "verification that cannot fail - fix or mark intentional"
```

## Limitations

- Python only.
- Static analysis. Nothing is executed, so a fail path that exists but is
  unreachable is not caught — see P12.
- Heuristic notion of "verification-shaped". A check named in a way the
  heuristic does not recognise will be missed.
- Filenames matter to it, which means unusual project layouts may need the
  suppression marker more than tidy ones.
- Single author, unreviewed, no CI. Judge accordingly.

## Contributing

The useful contribution is a **false positive or a false negative**, with the
smallest file that reproduces it. Type B detection — reachability analysis for
fail paths that exist but cannot fire — is the open problem and the half this
tool does not solve.

## License

MIT. See LICENSE.

*Vincit Omnia Veritas.*

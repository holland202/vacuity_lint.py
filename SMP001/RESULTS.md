# SMP-001: results — `suite_mutation_probe.py` joins the repository (2026-10-31)

**Who:** Claude (Anthropic, Opus 5.5) wrote the tool in September 2026 and wrote this test, at Chad Holland's direction. Review level: direction only. **SELF-TESTED** in an x86_64 container (Python 3.13.18). Nothing has been independently reproduced. **NOT RUN** on Windows or on the S25.

## What could have gone wrong, first

- **The predictions were not blind.** A container run while surveying Drive came before the registration, and [PREREG.md](PREREG.md) says so. That run is the reason P4 exists. This result shows the numbers reproduce inside the repository and that the fix works. It does not show a prediction made without seeing the answer.
- **The tool had a real defect (P4).** Every run left a `_smp_cov/` directory in the suite's working directory: a coverage tracer `sitecustomize.py`, PATH shims and logs. Run against someone's repository, that leaves untracked files. If the user later puts that folder on `PYTHONPATH`, the stale tracer could load into their own Python processes. Fixed here; the directory is now removed after the run unless it existed beforehand.
- **The September write-up that travelled with the tool describes v1, not v2.** It says the theatre suite lets 6 mutants survive. v2 reports 4 survived and 2 NOT_EXERCISED, because v2 excludes lines the suite never runs. That write-up was written for a specific outside project and is deliberately not included here. The numbers below are v2's.
- **Same author on both sides.** The tool, the demo and this test are all Claude's.

## Raw output

The full outputs are in [output/](output/). The before-fix outputs come from the tool exactly as recovered, sha256 `8e9f91387ec812abe5aec38afd6957f332aeda13e686834328c4455fe539a74a`. The after-fix outputs come from `9650f6452ccd552a6a1e944f33f06a9319d223bf250ef2cb976ea0c32b79ded5`. The six-line fix is the only difference between the two.

```
before fix   P1 selftest exit=0
             P2 honest suite   counted: killed=6 survived=0 survived_out=0   score 100.0%  95% CI [54.1%, 100.0%]   exit=0
             P3 theatre suite  counted: killed=0 survived=4 survived_out=0   score 0.0%    95% CI [0.0%, 60.2%]     exit=1
                               2 site(s) NOT_EXERCISED (lines 13 and 15, the two 'return False' in dispatch_admits)
             SMP001/demo afterwards: _smp_cov/ present (untracked)
after fix    P1, P2 and P3: identical counts and exit codes; SMP001/demo unchanged
```

| | Prediction | Result |
|---|---|---|
| P1 | selftest exits 0 | **HELD** |
| P2 | honest suite: 6 killed, 0 survived, exit 0 | **HELD** |
| P3 | theatre suite: 0 killed, 4 survived, 2 NOT_EXERCISED, exit 1 | **HELD** |
| P4 | suite cwd byte-identical after a run | **HELD after the fix**. It failed before the fix, which is the defect. |
| P5 | the regression test fails without the fix | **HELD**: 1 failure with the fix removed, OK with it |
| P6 | vacuity_lint finds nothing in the new files | **HELD** (`no vacuous verification found`) |
| P7 | Windows / PowerShell, and S25 under Termux | **NOT RUN** |

The repository's own CI steps were also run locally after the change, all passing:
- `unittest discover -s tests`, `vacuity_lint.py --selftest` (20/20) and `mutation_probe.py --selftest`;
- the gate control (clean, then the intended VL002, then clean) and the fixture controls;
- the issue-7 and VL-FP-001 mutants (4/4 and 4/4), and the E17-B selftest (7/7).

## What this shows, and what it does not

- **Shows:** on this demo, the tool can give both answers. It scores a suite that checks behaviour at 100% and a suite that only prints counts at 0% (exit 1), and it separates "never ran this line" from "ran it and did not notice".
- **Does not show:** anything about a real project's suite. **n = 6 and n = 4 are tiny.** The tool prints its own warning to that effect, and the intervals are 54–100% and 0–60%.
- **Its mutation operators are conservative** (boundary swaps, boolean flips, and/or swaps). A score is a lower bound on what a fuller operator set would find.

## Open

- P7: Windows / PowerShell, and the S25.
- A first real target: one of Chad's own suites. The `sovereign-memory-layer` verifier is the obvious candidate, since its mutants are hand-written and this tool's are generated.

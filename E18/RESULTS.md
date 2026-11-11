# E18 results — absence-only tests

Status: **EXECUTED, SELF-TESTED.** Registered in [PREREG.md](PREREG.md) at
57b9b30 before the instrument existed; instrument and fixtures written after;
one pre-run correction recorded in [RUN_NOTES.md](RUN_NOTES.md). Container
run only. Not independently reproduced. Not run on the S25.

## Verdicts

| Prediction | Registered claim | Result | Verdict |
|---|---|---|---|
| P1 | 8/8 planted flagged, 0/8 controls flagged | `flagged 8/8 planted, escaped=[], wrongly_flagged=[], unexpected=[], detector_rc=1` | **PASS** |
| P2 | sabotaged instrument must be rejected | sabotage escapes `test_a1_secret_absent`, `test_a2_no_leak_no_flag`; selftest reports them and exits nonzero | **PASS** |
| P3 | ≥ 1 AL001 finding outside E18 fixtures in the pinned 4-repo public corpus | **54 findings in 93 test files** (sovereign-veritas 30, vacuity_lint.py 23, sovereign-memory-layer 1, veritas-eval-harness 0) + 1 parse error on a deliberately broken IE1 fixture | **PASS** |
| P4 | hand audit of all 54; device rerun; promotion decision | — | **NOT RUN (the door)** |

Verbatim console output: [output_console.log](output_console.log).

## What the counts do and do not say

54 function-level findings are **not 54 defects**. The registered limitation
holds and is visible in the data: this repository's own suite contributes 23,
and many are tests that the *scanner must not flag something* — e.g.
`test_tables_are_not_findings`, `test_main_appearing_only_in_comment_is_not_entry_point`
— whose presence halves plausibly live in sibling tests. Whether each finding
is (a) a genuine absence-only defect, (b) a deliberate pairing, or (c) a
detector false positive is exactly P4, and P4 was left unrun on purpose.
Until P4 runs, the defensible claim is: the pattern is real, statically
detectable, cheap to find (93 files, seconds), and present in every corpus
repo that has more than one test file.

Two findings quoted without classification, as examples of the shape:

- `sovereign-memory-layer tests/test_memory.py:73 test_threshold_is_strict` —
  one assertion, empty-satisfiable.
- `sovereign-veritas tests/test_planner.py:100 test_empty_plan_rejected_before_execution` —
  two assertions, both empty-satisfiable.

## Limitations

Registered in PREREG and unchanged: Python-only; static polarity cannot see
fixtures that guarantee non-empty input; deliberately two-sided suites flag
at function level. Self-tested: the instrument's author wrote its selftest.
The corpus is four repositories by one author — prevalence here says nothing
about other codebases.

## Provenance

Prior-art search, registration, instrument, fixtures, runs and this record by
Claude (Anthropic, model Claude Fable 5) on the owner's direction, 2026-11-11.
The owner had not reviewed any of it at commit time. No independent
reproduction. The novelty claim stays bounded as registered: new detector and
measurement; the underlying logic (vacuous satisfaction over an empty domain)
is old and credited in PREREG.

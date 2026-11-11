# E18 registration — absence-only tests: verification satisfied by the empty world

**Status: REGISTERED, NOT RUN.** This file is committed before the instrument
exists. Errors found later are recorded as dated deviations in RESULTS.md, not
edited away here.

## Question

Is "absence-only verification" — a test function whose every assertion is
satisfiable by empty output — a statically detectable and actually occurring
defect class, distinct from the published test-smell taxonomy and from this
repository's VL001–VL004 rules?

The defect: a test that only asserts what must NOT be there passes when the
subject under test produces nothing at all. A leak check asserting
`name not in page` passes when the page fails to render; a scanner test
asserting `findings == []` passes when the scanner reads zero files. Three
specimens arose in the author's repositories in the week before registration:
a dashboard leak suite that needed presence assertions added before its
absence assertions meant anything; a release-manifest check that verified a
frozen copy while the live file drifted; this repository's own historical
empty-scan defect (clean verdict over a tree it never read, fixed at 93976dc).

## Prior art searched before registration (2026-11-11, searches run by the instrument's author)

- Ball & Kupferman, "Vacuity in Testing" (TAP 2008): semantic vacuity —
  whether specification elements affect a pass — detected by re-running tests
  against weakened specifications. Dynamic, specification-level. No static
  analysis of assertion polarity. https://www.cs.huji.ac.il/~ornak/publications/tap08.pdf
- "Oracles That Cannot Fail: Anchoring and the Expectation That Moves With the
  Fault" (arXiv:2608.17214, 2026): oracle *provenance* (expected values
  derived from the code under test). Orthogonal axis; states that existing
  linters and smell detectors do not implement even its predicate.
- testsmells.org taxonomy (19 smells, tsDetect lineage): nothing covers
  all-negative assertions. Closest are Empty Test (no statements), Unknown
  Test (no assertions), Redundant Assertion (self-comparison) — all different.
- Model checking's antecedent-failure vacuity (Beer et al. lineage) is the
  same logic — a universally quantified property over an empty set — which is
  why the concept is NOT claimed as new. What is claimed: a named, static,
  assertion-polarity detector for Python test functions, with registered
  self-tests and a measured prevalence, does not exist in the searched record.

Novelty claim is therefore bounded: new detector and measurement, old logic.

## Instrument (specified before implementation)

`E18/e18_absence_lint.py`, standalone AST scanner; `vacuity_lint.py` is not
modified. Scope: functions whose name starts `test_` in files whose name
starts `test`. A finding **AL001** is a scoped function with at least one
recognized assertion, all of which are EMPTY-SATISFIABLE:

| form | classified EMPTY-SATISFIABLE when |
|---|---|
| `self.assertNotIn / assertNotEqual / assertNotEquals / assertFalse / assertNotRegex / assertNotIsInstance / assertIsNone / assertNotAlmostEqual` | always |
| `*.assert_not_called()` | always |
| `self.assertEqual/assertEquals(a, b)` | a or b is a literal `0`, `""`, `b""`, `[]`, `{}`, `()`, `set()`, `None`, `False` |
| `self.assertTrue(x)` / plain `assert x` | x is `not …`; `… not in …`; `… != …`; `… is None`; `len(…) == 0`; `… == <empty literal as above>` |

Everything else recognized (assertIn, assertEqual to non-empty, assertRaises,
assertGreater, assertIsNot, bare positive asserts, …) is POSITIVE; one
positive assertion clears the function. Functions with zero recognized
assertions are out of scope (Unknown Test territory, IE1-B). `assertIsNot` is
deliberately conservative (POSITIVE). Exit codes follow the house rule:
1 findings, 0 clean, 2 could-not-look (and zero scanned test files is exit 2,
never a clean verdict — the 93976dc lesson).

Fixtures are generated at run time in a temporary directory by
`E18/build_fixtures.py` (never committed, so the repository's own CI scan
tree is unchanged): 8 planted absence-only functions (one per table row,
including a two-negative function and a mock-only function) and 8 controls
(two-sided, positive-only, assertRaises-only, zero-assertion, length-positive,
mixed, non-test helper with negatives, positive literal + one negative).

## Predictions, registered before any run

- **P1 (selftest):** the detector flags exactly the 8 planted absence-only
  functions and none of the 8 controls. Refuted by any mismatch in either
  direction.
- **P2 (anti-vacuity):** `--sabotage` reclassifies the three pure-negative
  unittest methods (assertNotIn, assertNotEqual, assertFalse) as POSITIVE;
  the selftest must then exit nonzero naming the escaped fixtures. Refuted if
  the sabotaged selftest exits 0 — the selftest would be unable to reject a
  broken instrument.
- **P3 (prevalence):** scanning the test files of four public repositories at
  the commits pinned below, AL001 reports at least one finding outside E18's
  own fixtures. Refuted if zero findings. No count is predicted, only
  existence; the corpus was chosen before the detector existed and is all
  public, so every reported path can be published.
- **P4 (left unrun — the door):** a hand audit of every P3 finding,
  classifying each as (a) genuine absence-only defect, (b) deliberate pairing
  whose presence half lives in a sibling test, or (c) detector false positive;
  plus an S25/Termux device rerun; plus the owner's decision whether AL001
  joins the main scanner's rule set.

## P3 corpus, pinned

| repo | commit | test files |
|---|---|---|
| holland202/vacuity_lint.py | 72345ff3672a | 23 |
| holland202/sovereign-veritas | 13c663b3a3b0 | 57 |
| holland202/sovereign-memory-layer | 6262dbe362c7 | 12 |
| holland202/veritas-eval-harness | 993f7e389403 | 1 |

Private repositories on the author's account are excluded by design: results
publish in this public repository.

## Known limitations, declared now

Static polarity cannot see a fixture that guarantees non-empty input, so a
deliberately two-sided suite will still flag at function level when its
presence half lives in a sibling test — P4(b) exists for exactly that. The
assertion table is Python/unittest-plus-plain-assert only. Message strings in
the detector avoid this repository's failure-text trigger substrings so the
new files do not perturb the fixture-expectation CI step.

## Provenance

Candidates generated, prior-art searches run, registration written and the
instrument to be implemented by Claude (Anthropic, model Claude Fable 5), on
the owner's direction of 2026-11-11 ("create something novel", with standing
authorization for repository changes). Human review level: the owner had not
reviewed this registration when it was committed. Self-tested will be the
strongest label any result here can carry.

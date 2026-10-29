# E17-B: Is E17's helper result decided by where the helper lives?

Status: **REGISTERED, NOT RUN.** This file is committed alone, before any E17-B fixture, script or run exists.
Registered 2026-10-29.

## Why

In E17 ([RESULTS.md](../E17/RESULTS.md)), case H1 broke `add` and turned the shared assertion helper into a no-op, leaving the test files unchanged. swarm-verify 1.3.1's `ci` passed it in Node and withheld the pass in Python. E17's P4 had predicted a miss in both, so its Python half was refuted. E17 named an explanation it did not test: the helper's location. The Node helper is `assertions.mjs` at the repository root; the Python helper is `tests/helpers.py`.

The simplest rival is that the two languages are handled differently. E17-B moves the helper across the boundary in both languages, so the two explanations predict different outcomes.

## What the source says (VERIFIED FROM SOURCE; behaviour still to be tested)

In the pinned tarball (`swarm-verify-1.3.1.tgz`, integrity below), `package/dist/gates/independent-verification.js` (sha256 `ae353ef6ff57bfcb96a22ff930e8f4556a5c3a6bca69446ee74be4fa8e8e6a18`):

- `readUnderBaseTests` (line 1065) collects the patch's changed files that are not newly added **and** satisfy `isTestFile` (line 1067). If there are none, it returns without re-running anything. Otherwise it writes back the base's versions of those files, re-runs the checks over the patch's source, then restores the patch's versions.
- `isTestFile` (lines 1106–1108) is a path rule:
  `/(^|\/)(__tests__|tests?)\/|(\.|_)(test|spec)\.[cm]?[jt]sx?$|(^|\/)test_[^/]*\.py$|_test\.py$/`

The same rule is in the upstream source at `moonrunnerkc/swarm-orchestrator` `66b4212745d208de136826d2fb6dd0e2e584f4f6` (2026-10-23): `src/gates/independent-verification.ts`, filter at line 1600, `isTestFile` at line 1637.

Read this way, a changed helper triggers the base-test re-run exactly when its path matches the rule. `tests/helpers.py` matches (a `tests/` segment). `assertions.mjs` at the root does not. Reading is not running, so E17-B tests it.

## Instrument (unchanged from E17)

- **swarm-verify 1.3.1** from the npm registry, integrity `sha512-LfvEhFPkECPKj8OTM6ZPEf6Inl4lZzGeVhDSgyjNzVqHxf32nWxRK2SVSCMjj3sFcSNOTbD/FPf9VrWx7WHKxA==`. The runner refuses any other tarball. If the package cannot be downloaded, E17-B is reported NOT RUN.
- Run as `swarm-verify ci --patch <file> --json` from the fixture repository at its base commit; Python runs add `--install`.
- **Outcome rule, registered now** (E17 adopted it as a recorded deviation; here it is the registered rule): E17's `classify()` in `E17/run_e17.py`, imported, not copied.
  - **PASS:** `regression` is `pass`.
  - **NOT PASS:** `regression` is `fail` or `unmeasured`.
  - **COULD NOT LOOK:** no `swarm.ci.v1` line, a refusal, the patch not applied, a failed dependency install, or the tests check saying its runner is not installed.
  - The exit code is recorded but not used: without a task oracle it is nonzero for every patch (E17 RUN_NOTES, deviation 1).
- Each case is run twice. If the two runs disagree, the case is UNSTABLE and carries no verdict.

## Fixtures (written after this file, frozen before any run)

E17's fixture constants (`E17/fixtures/fixtures.py`), its `uv.lock`, and its build functions (`E17/build_fixtures.py`) are imported, not copied. Every base keeps E17's two tests (`add(2, 3) == 5` and `add(0, 0) == 0`, both called through the helper) and E17's helper bodies. Only the helper's path changes.

| Base | Language | Helper path | Matches the path rule? | Collected by the language's runner? |
|---|---|---|---|---|
| `base_helper` (E17's) | Python | `tests/helpers.py` | yes | no (not `test_*.py`) |
| `base_helper_root` | Python | `helpers.py` | no | no |
| `base_helper_near` | Python | `tests_support/helpers.py` | no (`tests_support` is not a `tests` segment) | no |
| `base_helper` (E17's) | Node | `assertions.mjs` | no | no |
| `base_helper_tests` | Node | `tests/assertions.mjs` | yes | no (Node's default patterns use `test/`, not `tests/`) |

The tests import the helper from its new path. The last column is checked by the pre-seal gate (the base suite must report exactly 2 tests), not assumed.

**Cases.** The control patches are E17's C0 (`a + b` becomes `b + a`, tests untouched) and C2 (`add` returns `a * b`, tests untouched). The H1 patches are E17's: broken `add` plus the helper made a no-op, with the test files unchanged.

| Case | Base | Patch | Expected |
|---|---|---|---|
| Python `H1` | `base_helper` | E17's H1, **byte-identical** (patch sha256 starts `676211f74c2f`) | NOT PASS (replicates E17) |
| Python `C0-h`, `C2-h` | `base_helper` | C0, C2 | PASS, NOT PASS |
| Python `H1-root` | `base_helper_root` | H1 with the helper at `helpers.py` | **PASS** (missed) |
| Python `C0-root`, `C2-root` | `base_helper_root` | C0, C2 | PASS, NOT PASS |
| Python `H1-near` | `base_helper_near` | H1 with the helper at `tests_support/helpers.py` | **PASS** (missed) |
| Python `C0-near`, `C2-near` | `base_helper_near` | C0, C2 | PASS, NOT PASS |
| Node `H1` | `base_helper` | E17's H1, **byte-identical** (patch sha256 starts `d71f91e6332b`) | PASS (replicates E17) |
| Node `C0-h`, `C2-h` | `base_helper` | C0, C2 | PASS, NOT PASS |
| Node `H1-tests` | `base_helper_tests` | H1 with the helper at `tests/assertions.mjs` | **NOT PASS** (caught) |
| Node `C0-tests`, `C2-tests` | `base_helper_tests` | C0, C2 | PASS, NOT PASS |

15 cases, 30 runs. E17 ran no controls on its helper bases; `C0-h` and `C2-h` add them.

**Pre-seal integrity gate (no swarm-verify).** Run with each project's own runner, as in E17. The fixtures and the gate's output are committed before any swarm-verify run.
- Every base suite passes and reports exactly 2 tests.
- Every base suite fails against broken code.
- Every case's own patched suite passes, except the C2 cases, which fail.
- Both replication patches are byte-identical to E17's (sha256 equal to `E17/fixtures/manifest.json`).

## Predictions

| ID | Prediction | Exact criterion |
|---|---|---|
| P1 | The controls behave | On every base, C0 is PASS and C2 is NOT PASS. A base where either fails carries no H1 verdict |
| P2 | E17 replicates | Python `H1` NOT PASS; Node `H1` PASS |
| P3 | A Python helper at the root is missed | Python `H1-root` PASS |
| P4 | A Python helper beside the tests, in a directory not named `tests`, is missed | Python `H1-near` PASS |
| P5 | A Node helper in `tests/` is caught, by the base-test re-run | Node `H1-tests` NOT PASS, **and** its tests check lists `tests/assertions.mjs` in `baseTestsFiles`. NOT PASS by any other route counts as REFUTED for the mechanism and is reported separately |

**Reading the result, fixed now:**
- P1–P5 all hold: the location explanation is supported, and specifically the path rule. Language is not the cause in these fixtures.
- P5 fails while P3 and P4 hold: the path rule alone does not decide Node, so something language-specific remains.
- P3 or P4 fails: something beyond the path rule catches a moved helper in Python (for example, following imports), which contradicts the source reading.
- P2 fails: E17 does not replicate, and every other verdict is reported but marked unreliable.

## Anti-vacuity

- The registered outcomes include both PASS and NOT PASS among the H1 variants, and both among the controls on every base. An instrument stuck on either answer cannot satisfy P1–P5 together.
- The C2 controls show NOT PASS is reachable on every new base. The C0 controls show PASS is reachable.
- **`--sabotage`** in the evaluator flips every H1-variant outcome in the recorded results before scoring. The evaluator must then report fewer held predictions and exit 1. This checks that the verdict is computed from the results rather than printed.

## SWAY Amendment 4 rows

| Row | Triggered? | Answer |
|---|---|---|
| C-PRIVATE | No | The fixtures are constructed and contain no data about people. Raw `swarm.ci.v1` records may contain paths inside Claude's workspace, which are not people's data. |
| C-DESIGN | Yes | The claim is causal: helper location decides the outcome. **Design:** controlled experiment on constructed fixtures, one factor (helper path) varied with everything else held fixed, crossed with language. **Strongest claim supported:** causal, within these fixtures, swarm-verify 1.3.1 and this machine. Out of scope: catch rates on real patches, other tools, other versions. |
| C-HOLDOUT | Yes | E17 already observed the two replication cases, so they are not counted as tests of the new hypothesis. P2 is a replication check only. P3–P5 test cases nobody has run. Predictions were derived from the source, not from any swarm-verify output on the new fixtures. |
| C-SYNTH | Yes | The fixtures are generated by a script from a hand-written data file. **Classes:** 8 cases are expected PASS and 7 NOT PASS. **Distinct kinds:** 15 distinct patches, each run twice; no other repeats. **Named sample for a person to look at:** the three new H1 patches, `python/H1-root`, `python/H1-near` and `node/H1-tests`. Until the owner has looked at them, P3–P5 are reported but do not count toward the claim. |

## Pre-mortem

1. **A new Python base fails for an import reason** (the root module or the `tests_support` namespace package not found). swarm-verify would then read `fail` for reasons unrelated to the helper. Shows up in: the pre-seal gate. The run does not start until the gate holds.
2. **swarm-verify catches a moved helper by another route** (for example, its instrument-identity re-run), so a NOT PASS supports the wrong mechanism. Shows up in: P5's mechanism clause and the recorded `tests_detail`.
3. **The environment fails** (npm download, or `uv` through the workspace proxy) and every Python case reads COULD NOT LOOK. Shows up in: the COULD NOT LOOK lines. An environment fix may be applied and the affected cases rerun only if it touches no fixture, no instrument and no classifier. Every such fix is recorded. A run that produced PASS or NOT PASS is never rerun.

## What E17-B can and cannot say

- **Can:** whether moving the helper across swarm-verify 1.3.1's path rule flips `ci`'s outcome, in Node and in Python, on these fixtures, on one machine.
- **Cannot:** a catch rate for real agent patches; anything about other versions or other tools; anything about helpers loaded implicitly (for example `conftest.py`) rather than by import.
- **Self-tested.** Fixtures, runner and run are by this repository's side. It is an outside check of swarm-verify, not an independent reproduction of E17-B. Run in Claude's workspace, not on the owner's device.

## Communication

The tool's author has not been contacted about E17 or E17-B. After results exist, Claude drafts a note. Whether and when it is sent is the owner's decision, because it goes out under his name.

## Left unrun

- A helper loaded implicitly by the runner: pytest's `conftest.py`, and vitest setup files.
- A Node helper in `test/` (singular), where Node's own runner also collects the helper as a test file.
- Reproduction of E17-B by someone outside this repository.

## Provenance

Drafted by Claude (Anthropic, Claude Opus 5.5) on 2026-10-29, after the owner delegated the session's path to Claude. The source reading above was done by the same AI that wrote the predictions. No fixture existed and nothing was run. Not reviewed line by line by Chad.

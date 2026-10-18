# E17: Can the verifiers that reward terminal agents fail? A static scan of Terminal-Bench

Status: REGISTERED, NOT RUN. This file is committed alone, before any harness exists and before any Terminal-Bench
test file has been opened. Registered 2026-10-18 by Claude (Opus 5.5), at Chad Holland's direction (direction only;
not reviewed line by line).

## Why

Agents such as Terminal-RSI (Yang et al., arXiv:2610.22192, 2026-10-15) are trained on rewards computed by
benchmark verifiers: a run counts as "verified" or a "strict success" when a task's tests pass. A verifier that
cannot fail rewards whatever the agent did. This asks how much of that the tools in this repository can see in one
widely used benchmark, Terminal-Bench. The paper was brought to the maintainer's attention by ChatGPT (OpenAI); the
connection to Vacuity Lint was proposed by Claude. Neither implies endorsement by anyone.

Terminal-Bench already reviews its verifiers against reward hacking with adversarial "cheat trials" and a
hacker-fixer loop (`docs/TASK_REVIEW_AUTOMATION.md` in the target). The expected answer is therefore "very little",
and the predictions say so. A null result is still a result: it bounds what a syntactic scan adds to that review.

## What was looked at before registering

Only file names and counts (below), the target's README, `docs/task-template.toml`, and a grep of its docs for
"reward". No test file, `test.sh`, or task source was opened; no scanner was run on the target.

## Target (pinned)

- `harbor-framework/terminal-bench` at `2e29ca91d5f1cb6fb60924bf867acc755565c044` (2026-10-15), Apache-2.0. Not
  vendored here; the harness takes a checkout path and checks the commit.
- Population C (current): the 66 directories under `tasks/`. Each has `tests/test.sh` and a `tests/` directory;
  122 `.py` files under `tasks/*/tests/`, in 63 tasks. Which published dataset version this corresponds to (the paper
  reports 2.1, 3.0 and 4.0) is not established here.
- Population L (legacy): the 90 directories under `legacy/`, 108 `.py` files under `legacy/*/tests/`.
- Unit of analysis: each task's `tests/` directory, and every `.py` file in it (recursively).

## Instruments

- **I1.** `vacuity_lint.py` 2.0.0, sha256 `3cb0d07d4d5b807132a6a82bef50e09051d4fab35e00449e4cf435745a406971` (this
  repository at `c6064a9`), run with `--format json` once per task `tests/` directory. Recorded per task: exit code,
  rule IDs. Run under Python 3.13 (parse results depend on the Python version; recorded).
- **I2.** A measurement written for this experiment (`E17/run_e17.py`), standard library only, not part of
  Vacuity Lint. For every function or method whose name starts with `test` in every `.py` file under `tests/`, it
  classifies the body (docstring excluded), using the AST only:
  - **E (empty):** every statement is `pass`, `...`, or a bare constant expression.
  - **N (no fail statement, no call):** no `Assert`, `Raise` or `Call` node anywhere in the body. E is a subset of N.
  - **H (helper-dependent):** no `Assert` or `Raise` node, but at least one `Call` (it can fail only through what it
    calls, e.g. `pytest.fail`, a helper, or an exception).
  - **A:** at least one `Assert` or `Raise` node.
  Recorded per function: population, task, file, name, class.
- **Hand check (Claude).** Every I1 finding and every E or N function is read and labelled: **vacuous** (cannot
  fail), **setup-dependent** (empty body, but module imports or fixtures can still fail the test), or **false
  positive** (I1 only). This is self-tested judgement, not independent.

Not scanned: `tests/test.sh`, which turns test results into the reward. Vacuity Lint reads Python only. See U1.

## Predictions

Counts are per population. "Task with a finding" means I1 exit 1 on that task's `tests/`.

- **P1.** C: at most 3 of 66 tasks have an I1 finding.
- **P2.** L: at most 6 of 90 tasks have an I1 finding.
- **P3.** C: 0 functions classed E. L: at most 2.
- **P4.** C and L together: at most 5 functions classed N.
- **P5.** Of all I1 findings across C and L, if there are any, at least half are hand-labelled false positive
  (pytest-style verifiers declare `test_` functions, which Vacuity Lint counts as a fail path, so its findings here
  are expected to land on helper files). Vacuously held if there are none; reported as such.
- **P6.** H is under 25% of all classified functions in C, and under 25% in L. This is the weakest prior here: no
  test body has been seen.
- **P7 (determinism).** Two runs give byte-identical canonical results (equal SHA-256 digest).

## Anti-vacuity controls

- **K1.** I1 on a planted directory containing a `verify_planted.py` that prints `[FAIL]` and exits 0: exit 1,
  VL002. Shows I1 can fire in this harness.
- **K2.** I2 on a planted `test_planted.py` with one empty test, one test calling a helper, and one test with an
  `assert`: exactly one E, one H, one A. Shows I2 can return each class.
- **K3 (known blind spot, predicted).** I1 on the same planted `test_planted.py`: exit 0, no finding. This is the
  IE1 gap (`independent/IE1/`), registered as expected rather than discovered.
- **Sabotage.** `run_e17.py --sabotage` makes I2 ignore `Assert` nodes. K2 must then report the `assert` test as N,
  and the harness must exit 1.

## Limits

- Static and syntactic. A test classed A can still be unable to fail (an always-true assertion, an unreachable
  branch); a test classed E can still fail through imports or fixtures. Nothing is executed.
- The reward path (`test.sh`) is not examined, so a verifier whose shell wrapper ignores pytest's exit status would
  be missed entirely.
- One benchmark, one commit. Says nothing about the verifiers or results reported in the Terminal-RSI paper.
- Self-tested: Claude wrote this registration, will write I2, and does the hand check.

## Open, not run

- **U1.** The reward wiring: does each `tests/test.sh` make the reward depend on the tests' exit status? Needs a
  shell-aware check and its own registration.

## Provenance

Claude (Anthropic, Opus 5.5) wrote this registration → human validation: not performed → human editing/curation:
direction by Chad Holland → human responsibility: Chad Holland. Human review level: direction only.

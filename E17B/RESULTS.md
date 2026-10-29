# E17-B results: where the helper lives decides it, not the language

Status: **EXECUTED, SELF-TESTED.** Run 2026-10-29 in Claude's workspace. Not independently reproduced. Registration: [PREREG.md](PREREG.md) (`6f9f025`). Pre-run decisions: [RUN_NOTES.md](RUN_NOTES.md), sealed with the fixtures at `dfc065b` before any swarm-verify run. Raw records: `output/results.json` (`7e4d96d`).

Under the registration's C-SYNTH row, **P3–P5 do not yet count toward the claim.** The owner has not yet looked at the named sample: `fixtures/patches/python/H1-root.diff`, `fixtures/patches/python/H1-near.diff`, `fixtures/patches/node/H1-tests.diff`.

## What could have gone wrong, first

- **Self-tested end to end.** The same AI read swarm-verify's source, wrote the predictions, built the fixtures and the scorer, ran it and wrote this.
- **5 of 5 confirms a reading of the source; it is not a surprise.** The predictions came from reading `isTestFile` and `readUnderBaseTests`. The two that could have broken the reading were P4 (is the rule lexical, so that `tests_support/` is outside it?) and P5 (does the base-test re-run run the whole suite in Node, or only the changed file?). Both held.
- **Deviations, both recorded before the run:** the gate is stricter than registered (RUN_NOTES 1), and the run started from the registration commit without waiting for a merge (RUN_NOTES 2).
- **A wrong number in a commit message.** The message of `7e4d96d` says `--sabotage` scores "0 of 5". The output (`output/sabotage_console.log`) says **1 of 5**: P1 still holds under sabotage, because the controls are not flipped. The commit message is not rewritten; this line corrects it.
- **Reviews that have not happened:** the owner's look at the C-SYNTH sample, any line-by-line review, any independent reproduction.

## Outcomes (pasted from `output_console.log`)

```
node   H1   PASS           regression=pass 
node   C0-h PASS           regression=pass 
node   C2-h NOT PASS       regression=fail fail
node   H1-tests NOT PASS       regression=unmeasured unmeasured
node   C0-tests PASS           regression=pass 
node   C2-tests NOT PASS       regression=fail fail
python H1   NOT PASS       regression=unmeasured unmeasured
python C0-h PASS           regression=pass 
python C2-h NOT PASS       regression=fail fail
python H1-root PASS           regression=pass 
python C0-root PASS           regression=pass 
python C2-root NOT PASS       regression=fail fail
python H1-near PASS           regression=pass 
python C0-near PASS           regression=pass 
python C2-near NOT PASS       regression=fail fail
P1 HELD: controls on all 5 helper bases
P2 HELD: python H1 NOT PASS (registered NOT PASS), node H1 PASS (registered PASS)
P3 HELD: python H1-root PASS (registered PASS)
P4 HELD: python H1-near PASS (registered PASS)
P5 HELD: node H1-tests NOT PASS (registered NOT PASS, by the base-test re-run); tests/assertions.mjs in baseTestsFiles on every run
VERDICT 5 of 5 as registered
DIGEST 5c3444dc07cb2be74c656b9fdf9fe979b5038aa4da95143bcdeb39c015d2a263
RECORDED not pinned yet: exit 0
exit=0
```

Both runs of every case agreed; no case was UNSTABLE or COULD NOT LOOK. Every run exited 1, as in E17, because no task oracle is supplied.

## The two catches, in swarm-verify's own words

Read from the raw records (the `tests` check's `detail`):

- **Node `H1-tests`:** "the patch changed tests/assertions.mjs, and the base's versions of those tests fail against the patch's source (calc.test.mjs:4:1 › 0:adds)". `baseTestsFiles` is `["tests/assertions.mjs"]` on both runs.
- **Python `H1`** (the replication): "the patch changed tests/helpers.py, and the base's versions of those tests fail against the patch's source (tests.test_calc:test_add)". This matches E17.

The misses (`H1-root`, `H1-near`, Node `H1`) read "2 runner-reported tests, 2 executed; outcome passed" or "2 collected, 2 passed", with no base-test re-run recorded.

## Predictions

| ID | Prediction | Result | Verdict |
|---|---|---|---|
| P1 | Controls behave on all 5 helper bases | C0 PASS and C2 NOT PASS on every base | **HELD** |
| P2 | E17 replicates | Python H1 NOT PASS, Node H1 PASS | **HELD** |
| P3 | Python helper at the root is missed | PASS | **HELD** |
| P4 | Python helper in `tests_support/` is missed | PASS | **HELD** |
| P5 | Node helper in `tests/` is caught by the base-test re-run | NOT PASS, `tests/assertions.mjs` in `baseTestsFiles` on both runs | **HELD** |

Under the registered reading, all five holding supports the location explanation, and specifically the path rule. In these fixtures, language is not the cause.

## What this shows, and what it does not

- **Shows (implementation, on these fixtures, swarm-verify 1.3.1):** the same weakened helper is caught or passed depending only on whether its path matches `isTestFile`. The Python helper is caught at `tests/helpers.py` and passed at `helpers.py` and at `tests_support/helpers.py`. The Node helper is passed at the root and caught at `tests/assertions.mjs`.
- **Shows:** the boundary is lexical. A directory beside the tests but not named `tests` is outside it.
- **By the source reading, not by this run:** the same applies to any helper path the rule does not match (for example `testing/` or `test_utils/`), and upstream `main` at `66b4212` has the same rule. Neither was run.
- **Does not show:** a catch rate on real agent patches; anything about helpers loaded implicitly (`conftest.py`, vitest setup files); anything about other versions or other tools.
- **For E17:** this supports the explanation E17's RESULTS.md gave for its P4 refutation. E17's records are not edited.

## Candidate direction for the tool (a proposal; nothing is sent)

swarm-verify already follows imports from its instrument configuration (`instrument-identity`). Applying the same closure from the test files would put any changed module a test imports under the base-test re-run, wherever it lives. That is the tool author's decision. Whether he is told, and when, is the owner's.

## Still open

- **The owner's look at the C-SYNTH sample.** Until then P3–P5 do not count toward the claim.
- Helpers loaded implicitly: `conftest.py`, vitest setup files.
- A Node helper in `test/` (singular), which Node's own runner also collects as a test file (checked in RUN_NOTES: it does).
- Reproduction by someone outside this repository.

## Provenance

Run and written up by Claude (Anthropic, Claude Opus 5.5), 2026-10-29, after the owner delegated the session's path to Claude. Every outcome above is pasted from `output_console.log` or read from `output/results.json`. Not reviewed line by line by Chad.

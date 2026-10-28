# E17 run notes: decisions and deviations recorded before any E17 run

Written 2026-10-28, after the fixtures were built and gated but **before swarm-verify was run on any E17 fixture**. Everything below was found either while building the fixtures or on throwaway repositories outside E17. Those smoke repositories used a different function, `mul`, and different file names, and are not part of the results.

## Deviations from PREREG.md

1. **Outcome rule: read `regression`, not the exit code.** PREREG.md defined PASS as exit 0 and `regression: pass`. On a throwaway Node repository, an honest behaviour-preserving patch came back `regression: pass`, `verified: false`, exit **1**. The exit code also reflects task verification, which needs `--oracle`, and E17 supplies no oracle. Under the registered rule, every case would be NOT PASS: C0 and C1 would fail, and no verdict would be possible. The classification therefore reads `regression` only, which is the field swarm-verify's own test for this claim asserts (`attack-families.integration.test.ts`). The exit code is still recorded for every run. The exact rule is in `run_e17.py`'s docstring.
2. **Python runs use `--install`.** Without it, a fresh checkout has no pytest. On a throwaway Python repository, that came back `regression: unmeasured` because "pytest is not installed". `--install` is the tool's documented flag for installing from the lockfile.
3. **Python fixtures add `[tool.uv] native-tls = true`.** In Claude's workspace, outbound HTTPS goes through a proxy whose certificate authority is in the system store. swarm-verify builds its child environment without the proxy's certificate variables (by design: "no credentials"), so `uv sync` failed with `invalid peer certificate: UnknownIssuer`. Telling uv to use the system store fixed it on the throwaway repository. The setting is harmless on any other machine, and the lockfile did not change. This is an accommodation of Claude's workspace, not a change to what is measured.
4. **A fixture-gate defect was caught by the gate and fixed before sealing.** The first gate run executed bare `node --test`, which ignores K1's weakening (it lives in the `package.json` test script). Node K1 then failed its own suite, 33/34. The gate now runs the declared `npm test`, and holds at 34/34.

## Implementation details the registration leaves open

- H1 needs a base where the tests compare through a helper, so each language has two bases: `base` and `base_helper`. Both are in `fixtures/fixtures.py`.
- The test names are `adds` / `adds zeros` (Node) and `test_add` / `test_zeros` (Python). That way, K1's `-k 'not test_add'` deselects one test and not both.
- **COULD NOT LOOK** is decided before `regression` is read: no `swarm.ci.v1` line, a `refusal`, a patch not applied, a failed dependency install, or a tests check saying its runner is not installed.

## State at seal

- `fixtures/fixtures.py` is the single source. `fixtures/patches/` holds the 26 patches it produces. `fixtures/manifest.json` gives each patch's sha256 and deterministic base commit; a second build produced identical values. `fixtures/gate.json` holds the 34/34 gate output.
- `run_e17.py --selftest`: 2/2 checks. Four deliberate breakages of the classifier were each caught; a no-op edit was not.
- The instrument tarball's sha512 matched PREREG.md before any use.

## Provenance

Claude (Anthropic, Claude Opus 5.5), 2026-10-28, at Chad Holland's direction. Not reviewed line by line by Chad.

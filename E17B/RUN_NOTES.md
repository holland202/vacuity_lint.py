# E17-B run notes: decisions and deviations recorded before any E17-B run

Written 2026-10-29, after the fixtures were built and gated but **before swarm-verify was run on any E17-B fixture**.

## Deviations from PREREG.md

1. **The gate is stricter than registered.** PREREG.md requires each failing suite only to fail. A deliberate breakage of the gate (a wrong import in `base_helper_near`'s tests) showed that a collection error then counted as the expected failure: "base suite fails against broken code" and `C2-near` were marked OK while the base itself could not import its helper. The gate as committed requires every suite run, passing or failing, to report exactly 2 tests. With that breakage the gate fails 3 checks (24/27 at the time, before the tightening); unbroken it holds 27/27.
2. **The run starts from the registration commit, not a merge.** PREREG.md was committed alone at `6f9f025` (2026-10-29 06:30 −04:00) and pushed before any fixture existed. The owner delegated the session's path to Claude on 2026-10-29. The run does not wait for the owner to merge the registration. Merging stays his.

## Implementation details the registration leaves open

- `e17b_fixtures.py` imports E17's constants and builds each new base by moving one file and rewriting the one import line that names it (a `ValueError` if the line is not found exactly once). `build_fixtures.py` imports E17's build functions and points them at E17-B's data. `run_e17b.py run` calls E17's `main()`. Nothing about building, running or classifying is copied.
- Python bases keep E17's `pyproject.toml`, including `[tool.uv] native-tls = true` (E17 RUN_NOTES deviation 3), and E17's `uv.lock`.
- **P5's mechanism clause** reads `baseTestsFiles` from the `tests` check in every run's raw `swarm.ci.v1` record. E17's own Python H1 record carries the field (`["tests/helpers.py"]`), so it is serialized, not inferred.
- **Person-look sample (C-SYNTH):** `fixtures/patches/python/H1-root.diff`, `fixtures/patches/python/H1-near.diff`, `fixtures/patches/node/H1-tests.diff`. Claude has read all three. That does not satisfy the rule, which asks for a person.

## State at seal

- 15 fixtures. `fixtures/manifest.json` gives each patch's sha256 and deterministic base commit. A second build produced identical values for all 15.
- The two replication patches are byte-identical to E17's: Python H1 `676211f74c2f…`, Node H1 `d71f91e6332b…`.
- `fixtures/gate.json` and `fixtures/gate_console.log`: 27/27 gate checks hold. Every base suite reports 2 tests.
- Node's runner does not collect files under `tests/`. Checked on a throwaway copy of `C0-tests`, outside the fixtures: a file `tests/probe.mjs` that throws at load left the run at "# tests 2, # fail 0". The same file under `test/` was collected and failed ("# tests 3").
- `run_e17b.py --selftest`: 7/7. Five deliberate breakages of the scorer: three were caught. Two survived, and both are equivalent mutants. `f == "PASS"` → `f != "NOT PASS"` cannot change a result, because a licensed outcome is always one of the two. Dropping the sort of `baseTestsFiles` cannot change a single-file list, and swarm-verify sorts that list itself (`readUnderBaseTests`, `.sort()`).
- Environment for the run: Node v22.23.4, npm 10.9.9, uv 0.11.32, Python 3.13.18, x86_64, Claude's workspace.

## Provenance

Claude (Anthropic, Claude Opus 5.5), 2026-10-29, after the owner delegated the session's path to Claude. Not reviewed line by line by Chad.

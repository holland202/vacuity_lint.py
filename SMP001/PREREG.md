# SMP-001: registration — `suite_mutation_probe.py` joins this repository

**Registered:** 2026-10-31, before the tool was added to this repository and before any run inside it.
**Author:** Claude (Anthropic, Opus 5.5), at Chad Holland's direction. Review level: direction only.
**Status at registration:** nothing built or run in this repository.

## What could have gone wrong, first (disclosed before the run)

- **These predictions are not blind.** On 2026-10-31, before writing this file, Claude ran the tool once in a container while surveying Chad's Google Drive for unpublished work. That run produced the numbers predicted below, and it found the defect named in P4. This registration commits to that run reproducing in the repository, and to the fix doing what P4 says. It does not claim any prediction made without having seen the result.
- **Claude wrote both the tool (in September) and this test.** Everything here is SELF-TESTED. Nothing has been independently reproduced.

## What is being added

`suite_mutation_probe.py` v2 (1,581 lines, sha256 `8e9f91387ec812abe5aec38afd6957f332aeda13e686834328c4455fe539a74a` as recovered from Drive, dated 2026-09-14). Claude wrote it in September. It never reached any repository.

- **What it does:** it mutates a *runtime module* and runs a *separate test suite* as the judge, asking whether the suite notices the damage. That is the two-file, dynamic question. `vacuity_lint.py` is static, and `mutation_probe.py` mutates a script and runs that same script, so neither can ask it.
- **What it reuses:** it imports its mutation operators from `mutation_probe.py` (`eligible_nodes`, `apply_mutation`, `describe`), so the two tools cannot drift apart.

The demo under `SMP001/demo/` is a 20-line toy governor plus two suites. `suite_real.py` checks the governor's behaviour. `suite_theatre.py` calls it 1,235 times, prints large pass counts, and always exits 0.

## Predictions

- **P1.** `python3 suite_mutation_probe.py --selftest` exits 0.
- **P2.** Honest suite (`--source SMP001/demo/governor.py --suite "python3 suite_real.py" --cwd SMP001/demo`): killed=6, survived=0, mutation score 100.0%, exit 0.
- **P3 (the anti-vacuity control).** Theatre suite, same arguments with `suite_theatre.py`: killed=0, survived=4, and 2 sites NOT_EXERCISED (the two `return False` lines in `dispatch_admits`, which the theatre suite never reaches). Exit 1. If P2 and P3 do not differ, the tool cannot tell the two suites apart and P2 means nothing.
- **P4 (the defect, and the fix).** Before the fix, a run leaves a `_smp_cov/` directory, holding an injected `sitecustomize.py`, in the suite's working directory. After the fix, the working directory's tree is byte-identical before and after a run, for the honest-suite run and the theatre-suite run alike.
- **P5.** A regression test for P4 fails when the cleanup is removed from the tool.
- **P6.** `vacuity_lint.py` reports no findings on the new files.

## Left unrun (the door)

- **P7.** The same P1–P3 on Windows / PowerShell, and on the S25 under Termux. The tool has only ever run on Linux.

# Independent mutation-probe preservation review

**Verdict: FAILED — three reproducible file-preservation defects.** The ordinary honest and theatre controls behave as documented. A deliberate cleanup mutant is caught by the independent preservation oracle. Those passing controls do not prevent the probe from overwriting preexisting instrumentation files, deleting a preexisting backup, or changing CRLF source bytes during restoration.

Target: `holland202/vacuity_lint.py`, `c1ca2d4ee489b5d64285fa6600f46d5f948296a3`. `suite_mutation_probe.py` blob `040a894fbd18773217472ffa8e5767a24cf9f38c`, SHA-256 `9650f6452ccd552a6a1e944f33f06a9319d223bf250ef2cb976ea0c32b79ded5`. Adjacent operator SHA-256: `90180d53443c8297f1ef6a1ffefd671b04b4c22951e8de57c5ee91f18b4ee24d`. The probe blob matches `claude/suite-mutation-probe` at `0c1d3757a751768560dd28af031aa7bc7aee8503`.

Registration commit `604f0b6` precedes execution. Work branch: `chatgpt/smp-attack-20261031`, created locally because it was absent remotely. No production files were edited. Only synthetic demo copies in temporary directories were mutated; raw evidence includes the exact before/after bytes. Environment: CPython 3.12.14, Linux x86_64. This is a source-informed bounded review. The earlier attack brief was not recovered, so completing its entire intended scope is UNKNOWN, not claimed.

ChatGPT (OpenAI) designed and ran this review → human validation: not performed → human responsibility: Chad Holland.

## Execution

From the repository root:

```bash
python3 review/smp_chatgpt_20261102/review.py --out /tmp/smp-review-fresh
```

The review exits **1**, because A1–A3 violate the preservation criterion. [Runner stdout](runner.stdout), [stderr](runner.stderr), and [all case summaries](raw/summary.json) are saved. Each `raw/<ID>/command.json` records the actual command, exit code, hashes and changed paths; `stdout.txt` and `stderr.txt` preserve probe output. `before.json` / `after.json` list tree hashes, and the `before/` / `after/` directories save every changed file's bytes. A normal campaign JSON is retained when the probe produced one. All three failures were repeated in isolation, with the same outcomes; the separate `repro_A1/`, `repro_A2/` and `repro_A3/` directories preserve those runs and the adjacent `A*_repro.stdout` files record the review verdicts.

| Case | Required outcome | Actual result | Label |
| --- | --- | --- | --- |
| C0, honest suite | Exit 0, six killed / denominator six, byte-identical working tree | Held, 100% score, no changed paths | VERIFIED |
| C1, theatre suite | Exit 1, zero killed, four survived, two NOT_EXERCISED, unchanged tree | Held, 0% score, no changed paths | VERIFIED |
| C2, deliberately broken cleanup | Independent tree oracle catches instrumentation left behind | Caught, although the mutant probe reports exit 0 / 100% score | VERIFIED |
| A1, existing `_smp_cov` files | Preserve all existing bytes or refuse before changing them | Existing files overwritten/truncated; exit 0 / 100% score | FAILED |
| A2, existing `.mutbak` | Preserve existing backup or refuse | Existing user backup overwritten, then deleted; exit 0 / 100% score | FAILED |
| A3, CRLF source | Restore exact source SHA-256 | Source normalized to LF, restore check fails, exit 2; rescue backup and instrumentation remain | FAILED |

## A1 — preexisting instrumentation files are overwritten

Synthetic user files existed at `_smp_cov/sitecustomize.py`, `executed.txt`, `attach.log`, and `bin/python3`. The probe overwrote their contents and added `bin/python`. An unrelated `_smp_cov/mine.txt` survived, so the existing regression test's sentinel-only assertion does not detect this loss. The target source itself was restored; the user files were not. The probe still reports exit 0 and a 100% mutation score.

Repro: `python3 review/smp_chatgpt_20261102/review.py --case A1 --out /tmp/smp-a1-fresh`

Evidence: [command/outcome](raw/A1/command.json), [before hashes](raw/A1/before.json), [after hashes](raw/A1/after.json), [probe stdout](raw/A1/stdout.txt). Source: `make_coverage_env` opens fixed user-visible paths for writing and unlinks old log files. `probe` only remembers whether the directory existed and then leaves the modified directory in place. It neither refuses collisions nor restores their contents.

## A2 — an existing source backup is destroyed

The synthetic file `governor.py.mutbak` contained unrelated user data before execution. `shutil.copy2(source, backup)` overwrote it, and the final cleanup deleted it. The original target source was restored and the probe reports exit 0 / 100%, while the preexisting backup is gone.

Repro: `python3 review/smp_chatgpt_20261102/review.py --case A2 --out /tmp/smp-a2-fresh`

Evidence: [command/outcome](raw/A2/command.json), [before bytes](raw/A2/before/governor.py.mutbak), [before hashes](raw/A2/before.json), [after hashes](raw/A2/after.json). Source: `probe` constructs the fixed `<source>.mutbak` name, overwrites without an ownership/collision check, and unconditionally unlinks it on normal completion.

## A3 — CRLF source cannot be restored byte for byte

A valid demo source was converted to CRLF before the run. The probe reads it with universal-newline text mode and later writes normalized LF text. That changes the SHA-256. The restore check correctly notices and prints `FATAL: could not restore`, but the source is already changed. The finally block attempts the same restore a second time, prints the same fatal message, and exits before instrumentation cleanup. The `.mutbak` rescue copy retains the original CRLF bytes; those bytes are saved in the evidence before the review harness removes its temporary fixture.

Repro: `python3 review/smp_chatgpt_20261102/review.py --case A3 --out /tmp/smp-a3-fresh`

Evidence: [command/outcome](raw/A3/command.json), [fatal stderr](raw/A3/stderr.txt), [original bytes](raw/A3/before/governor.py), [changed bytes](raw/A3/after/governor.py), [rescue bytes](raw/A3/after/governor.py.mutbak). Source: `probe` reads `original` in text mode and `restore` writes that text rather than the original bytes. This is not a claim about Windows execution; it was reproduced on Linux using a CRLF file.

## Limits and handoff

These three attacks are synthetic engineering checks, not measurements of mutation-testing effectiveness on real research suites. There was no hostile external input, network interaction by the probe, or modification of a sealed repository source. The original selftest, full repository checks, Windows, Android, coverage-topology attacks, and all other cases from the unavailable earlier brief are **NOT TESTED / NOT RUN**. The cleanup mutant is a temporary copy; the production probe and mutation operators remain byte-identical to the pinned target.

Preserve the findings and raw output, make fixes separately, then rerun the exact positive, negative and failing cases. A unique temporary instrumentation directory, collision-safe backup handling and byte-preserving restoration are candidate fix directions, not implemented changes. GitHub publication remains blocked; the handoff includes this branch as a separate Git bundle for a draft PR targeting main.

# Bounded independent suite_mutation_probe review — preregistration

Date: 2026-11-02. Reviewer: ChatGPT (OpenAI), at Chad Holland's direction.

The requested work branch `chatgpt/smp-attack-20261031` was not present remotely and has now been created locally. The earlier attack brief could not be recovered from the repository or Library searches. This is a new, bounded, source-informed registration, not a claim to have completed every case in that missing brief.

Frozen target: `holland202/vacuity_lint.py`, main commit `c1ca2d4ee489b5d64285fa6600f46d5f948296a3`, `suite_mutation_probe.py` blob `040a894fbd18773217472ffa8e5767a24cf9f38c`. That blob is also on `claude/suite-mutation-probe` at `0c1d3757a751768560dd28af031aa7bc7aee8503`. Use the adjacent frozen `mutation_probe.py` operators. CPython 3.12.14, Linux x86_64. Other platforms are NOT TESTED.

Commit this registration before running any probe, self-test, or attack. The production probe, operators, main and Claude's branch must remain untouched. All source mutation occurs on synthetic temporary copies, never on repository originals. Save every command, exit status, raw stdout/stderr, JSON campaign, before/after file hashes and relevant original/resulting bytes. No scientific experiment or reserved research suite is authorized here.

| ID | Registered check | Prediction and defect rule |
| --- | --- | --- |
| C0 | Copy the existing tiny demo and run its honest suite; independently compare every file byte before/after | Exit 0, six killed mutants, denominator six; no source or working-tree changes. Failure of this expected positive is a review control failure as well as an observation. |
| C1 | Run the same demo with the theatre suite | Exit 1, zero killed, four survivors and two NOT_EXERCISED; distinguishes an ineffective suite from the positive. |
| C2 | Deliberately break cleanup in a temporary copy of the probe; run the honest suite | The independent byte/tree-preservation oracle must catch the leftover `_smp_cov` files, although the probe can still report a passing mutation score. A missed mutant invalidates the cleanup oracle. |
| A1 | Prepopulate `_smp_cov` with synthetic user files named `sitecustomize.py`, `executed.txt`, `attach.log`, `bin/python3`, plus an unrelated sentinel | Refuse before modification or preserve/restore all preexisting bytes and names. Silently overwriting or deleting these files is a reproducible data-preservation defect; survival of an unrelated sentinel alone is insufficient. |
| A2 | Prepopulate `<source>.mutbak` with unrelated synthetic bytes | Refuse before modification or preserve/restore that existing file. Overwrite/delete is a data-preservation defect. |
| A3 | Convert a valid synthetic demo source to CRLF; hash the exact bytes before and after a normal honest run | Exact source restore must retain CRLF and the original SHA-256. A normalization-induced restore failure is a defect under the advertised SHA-256 restoration promise; report any retained rescue backup. |

`VERIFIED` = executed criterion held. `FAILED` = executed reproducible contract violation. `UNKNOWN` = inconclusive evidence. `NOT TESTED` / `NOT RUN` = no execution. Record self-tests, Windows/Android, the missing original brief's remaining scope and any other cases as NOT RUN unless actually executed. Prefer a single isolated run per case; preserve earlier evidence if any runner repair requires repetition. Any new attack family needs a committed addendum before execution.

Deliver only the review directory and a draft-PR handoff on the requested work branch. No fixes, merges, publication or collaborator contact. GitHub writes are currently returning 403; provide an exact Git bundle if that remains unresolved.

Provenance line: ChatGPT (OpenAI) designed and ran this review → human validation: not performed → human responsibility: Chad Holland.

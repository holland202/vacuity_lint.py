# SMP-002 results (2026-11-02)

## What could have gone wrong, first

- **The probe could destroy user files.** ChatGPT's independent review (draft PR #30) found three ways, all reproduced here before any fix (P1):
  - existing `_smp_cov` files were overwritten;
  - an existing `.mutbak` was deleted;
  - a CRLF source was left changed after the run (exit 2).

  In two of the three cases the probe still reported **exit 0 and a 100% score** while it lost the user's files. The SMP-001 cleanup test only checked one sentinel file, so it could not see this.
- **P2 is only partly as registered.** ChatGPT's C2 control edits the exact cleanup line that the A1 fix removed, so its runner now stops with an AssertionError before C2 runs. The **full** runner therefore exits 1. That is a coupling of the control to the old layout, not a defect it found. Its other five cases were run one by one and all pass. **C2′** replaces C2 as the anti-vacuity control: with the new cleanup sabotaged, the leaked instrumentation directory must be found, and it is.
- **Self-fixed.** The fixes and C2′ are Claude's; the A1–A3, C0 and C1 cases are ChatGPT's. ChatGPT has not re-run its review on this fix.

## Raw output (`output/`)

P1, before the fix (`p1_chatgpt_runner_before.stdout`):
```
C0 VERIFIED exit 0 changed []
C1 VERIFIED exit 1 changed []
C2 VERIFIED exit 0 changed ['_smp_cov', '_smp_cov/attach.log', ...]
A1 FAILED exit 0 changed ['_smp_cov/attach.log', '_smp_cov/bin/python', '_smp_cov/bin/python3', '_smp_cov/executed.txt', '_smp_cov/sitecustomize.py']
A2 FAILED exit 0 changed ['governor.py.mutbak']
A3 FAILED exit 2 changed ['_smp_cov', ..., 'governor.py', 'governor.py.mutbak']
```
P2, after the fix, per case (`p2_case_*.stdout`):
```
C0 VERIFIED exit 0 changed []
C1 VERIFIED exit 1 changed []
A1 VERIFIED exit 0 changed []
A2 VERIFIED exit 0 changed []
A3 VERIFIED exit 0 changed []
```
The full runner after the fix (`p2_chatgpt_runner_full_after.stdout`): `AssertionError` at C2's sabotage line (`text.count(old) == 1`).

P3: `python3 -m unittest discover -s tests` ran 74 tests, OK. `suite_mutation_probe.py --selftest` exit 0. The new `tests/test_smp002_preservation.py` covers A1, A2, A3, no leftover in TMPDIR, and C2′.

## Predictions

| ID | Prediction | Result |
|---|---|---|
| P1 | before the fix: A1, A2, A3 FAILED; C0, C1, C2 VERIFIED | **HELD** |
| P2 | after the fix: all six cases meet their required outcome | **PARTLY**: C0, C1, A1, A2, A3 VERIFIED; C2 could not run (coupled to the removed line), replaced by C2′, which catches the sabotage |
| P3 | repository checks still pass; control scores unchanged | **HELD**: C0 6 of 6 killed, C1 0 killed, all tests OK |

## The fix (`suite_mutation_probe.py`)

- **A1:** instrumentation goes into a fresh `tempfile.mkdtemp(prefix="smp_cov_")` outside the user's tree, and is always removed. `<cwd>/_smp_cov` is never touched.
- **A2:** the backup gets a unique `tempfile.mkstemp` name beside the source.
- **A3:** the original **bytes** are kept and restored; mutants are written with `newline=""`.

## Open

- ChatGPT should re-run its review against this commit.
- Windows and Android are not tested.

Credit: findings A1–A3 by ChatGPT (OpenAI), at Chad Holland's direction.

Provenance: fixes by Claude (Anthropic, Opus 5.5), at Chad Holland's direction (2026-11-02, direction only) → human validation: not performed → human responsibility: Chad Holland.

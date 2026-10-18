# IE1: first independent evaluation of Vacuity Lint (Putluru Sandeep, 2026-10-18)

**Evaluator:** Putluru Sandeep (GitHub `sunny-kavixo`), who designed the cases, ran them on his own machine and
wrote the package. **Published with his agreement**, as confirmed to the maintainer on 2026-10-18.
**Instrument evaluated:** `vacuity_lint.py` 2.0.0 at `da5fe76ddcd660c2d21a89853623e905a0b33708` (`main` at the
time), scanner SHA-256 `3cb0d07d4d5b807132a6a82bef50e09051d4fab35e00449e4cf435745a406971`.
**His environment:** macOS 27.0.1 arm64, Python 3.14.5; pytest 9.1.1 for the separate pytest control.

This is one independent human evaluation, reproduced by two AI reruns (below). It is not a validation of
Vacuity Lint. The AI reruns confirm that his record is accurate; they add no independent case design.

## What failed or is weak (first)

No documented rule was broken. All three of his principal findings are limits:

1. **VL002 on a docstring: false positive with misleading wording.** A file whose only failure text is `[FAIL]` in a
   docstring gets `PRINTS_FAIL_ONLY` and exit 1, with the message "prints failure text 1x". Nothing is printed; the
   target runs and exits 0. `RULES.md` already says VL002 counts every string constant, docstrings included, so this
   is documented behaviour. The message wording is the defect. (He first called this an implementation bug, then
   corrected himself in the handoff; both statements are kept in his package.)
2. **An empty test function is not flagged.** `def test_empty(): pass` scans clean (exit 0), and pytest passes it.
   Declaring a `test_*` function counts as a recognized fail path, so a test body that cannot fail is invisible. This
   is a scope limit next to E16's known misses, not a rule violation. It is the most useful finding.
3. **An unreachable `raise` is not flagged.** `if False: raise ...` scans clean. This is the documented Type B
   reachability limit (self-test P12). Not new.

Also limiting: his 16/16 means the scanner did what he expected on 16 cases, four of which are known misses he
expected to scan clean. It is classification agreement, not 16 detections. His packaging step did not rerun the
scanner; the reruns below do.

## Contents

| Path | What | Changed? |
|---|---|---|
| `Vacuity-Lint-v2-Independent-Evidence.zip` | the package exactly as received, SHA-256 `14fc8f2e7075512abafd6f3e6f1e0cc3a3f2a5f3c887c05331473a5157798e1b` | no |
| `package/` | the same package, extracted | one difference, below |
| `claude_rerun.txt` | Claude's rerun, verbatim | — |
| `PROPOSALS.md` | two proposed changes arising from this evaluation; not registered, not implemented | — |

Git cannot store an empty directory, so `package/independent_cases/empty/` is missing from a checkout, and his
`verify_package.py` then stops at "Empty input directory". To run his verifier exactly as he did, extract the zip, or
run `mkdir -p package/independent_cases/empty` first. Nothing else in `package/` differs from the zip.

Start with `package/MAINTAINER_HANDOFF.md`, his authoritative interpretation.

## Reproduction 1: Claude (2026-10-18)

Run in the maintainer's cloud session (Linux x86-64, Python 3), with the repository's own `vacuity_lint.py`, not the
copy inside the package. Full transcript: `claude_rerun.txt`.

- All 19 files in `package/source_snapshot/` are byte-identical to the repository at `da5fe76`, so his results apply
  to the published tool, not only to his copy. `main` had not moved since he evaluated it.
- `SHA256SUMS` 56/56 OK; his `verify_package.py` PASS; self-test `20/20 checks passed`.
- The three reproductions give exactly his results: VL002 exit 1; empty test exit 0; unreachable raise exit 0. The
  two runnable targets print `documentation loaded` and `success` and exit 0.
- His driver: `independent_cases=16 failures=0`, exit 0. EGRR copies: 7 files, 6 verification-shaped, 0 findings,
  exit 0. Empty directory: exit 2. His `defective/` directory: exit 1, 5 findings (VL001, VL002, VL003, VL004, VL005).

## Reproduction 2: ChatGPT (OpenAI), 2026-10-18

Run by the maintainer with ChatGPT against the scanner inside the package. Reported to Claude as a summary; Claude
did not see ChatGPT's raw output. Reported: the same three results; 56/56 hashes; self-test 20/20; 16/16 cases; 7/7
EGRR inputs without findings; empty directory exit 2; defective directory exit 1 with five findings. Its
conclusion, as reported: the findings are reproducible within the tested scope, the VL002 correction is
appropriate, the empty-test and unreachable-path limits are genuine, and no scanner change is justified
automatically. Every number it reported matches Reproduction 1.

ChatGPT tested the package's copy of the scanner, which shows the package is self-consistent. The byte comparison in
Reproduction 1 is what ties it to the published code.

## What this does and does not establish

It establishes that an outside person, using cases he wrote, found Vacuity Lint 2.0.0 behaving as its documentation
says, including its documented blind spots, and that his record reproduces exactly. It does not establish precision
or recall on real code, correctness of the EGRR research files (scanned, never executed), or that a clean scan means
a check is sound.

## Provenance

The evaluation and the package: Putluru Sandeep → his own review → human responsibility for the package: Putluru
Sandeep. Whether AI tools helped him is not stated in the package. This record and `claude_rerun.txt`: Claude
(Anthropic, Opus 5.5) wrote them → human validation: not performed → human editing/curation: direction by Chad
Holland → human responsibility: Chad Holland. Human review level: direction only. ChatGPT's rerun was directed by
Chad Holland and is reported, not reproduced, here.

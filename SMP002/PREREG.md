# SMP-002: three file-preservation failures found by ChatGPT — registration (2026-11-02)

Written before any fix and before ChatGPT's suite was re-run here.

**Source:** ChatGPT (OpenAI), independent bounded review of `suite_mutation_probe.py` at `c1ca2d4`, published unchanged as draft PR #30 (`chatgpt/smp-attack-20261031`, head `2da6cc7`, preregistered at `604f0b6`). Its runner `review/smp_chatgpt_20261102/review.py` and its cases are used as they are.

## Findings (ChatGPT's labels)

- **A1:** existing user files in `<cwd>/_smp_cov/` are overwritten. The probe writes its instrumentation into a fixed directory in the suite's working directory.
- **A2:** an existing `<source>.mutbak` is overwritten, then deleted. The backup name is fixed.
- **A3:** a CRLF source cannot be restored byte for byte. The source is read in text mode and written back with LF; the probe exits 2 and leaves instrumentation behind.

## Fixes (to be built)

- **A1:** instrumentation goes into a fresh directory from `tempfile.mkdtemp()`, outside the user's tree, and is always removed afterwards. Nothing is written to `<cwd>/_smp_cov` any more.
- **A2:** the backup gets a unique name in the source's directory (`tempfile.mkstemp`, prefix `<name>.mutbak.`). An existing `.mutbak` is never touched.
- **A3:** the original **bytes** are kept and restored. Mutation reads and writes text with `newline=""`, so line endings are not translated.

## Predictions

- **P1 (before any fix, `main` at `c1ca2d4`):** ChatGPT's runner reports A1, A2 and A3 FAILED, with C0, C1 and C2 VERIFIED, and exits 1.
- **P2 (after the fixes):** ChatGPT's runner reports all six cases meeting their required outcome: C0 and C1 held, C2's broken-cleanup mutant caught, and A1, A2 and A3 preserved. It exits 0.
- **P3:** the repository's own checks still pass: `tests/`, the SMP-001 cleanup test, and the gate's selftests. The mutation scores on the controls are unchanged: C0 6 of 6 killed, C1 0 of 4 survived.

## Limits

Self-fixed, then judged by ChatGPT's cases, which are independent. ChatGPT has not re-run them on the fix. Not tested on Windows or Android.

Provenance: Claude (Anthropic, Opus 5.5), at Chad Holland's direction (2026-11-02, direction only) → human validation: not performed → human responsibility: Chad Holland. Findings by ChatGPT (OpenAI).

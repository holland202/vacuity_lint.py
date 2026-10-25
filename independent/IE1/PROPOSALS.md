# IE1 proposals: two changes the evaluation points to

**Status:** PROPOSED. Not registered, not implemented. Nothing in `vacuity_lint.py` has changed. Each needs the
maintainer's decision and, before any code, a registration with predictions, as E15 and E16 were done.

## IE1-A: VL002 wording

**Problem.** VL002's message says `prints failure text 1x`, but the rule counts any failure-oriented string constant,
including docstrings (`RULES.md`). In IE1's docstring case nothing is printed.

**Proposal.** Change the message to describe what was found, for example `contains failure text 1x but has no
assert, raise, or nonzero exit`. Rule ID, trigger and exit code stay the same.

**What must stay true.** The same files are flagged with the same rule IDs and exit codes, so IE1's 16 cases, the
self-test and E16 give the same classifications. Anything that matches on the old message text (tests, JSON
consumers) would need updating; the JSON `rule_id` does not change.

**Not proposed here:** separating docstrings from printed strings. That changes what VL002 flags and is a larger,
separate decision.

## IE1-B: an empty test function

**Update 2026-10-25:** registered, not run, in [IE1B/PREREG.md](../../IE1B/PREREG.md). Two owner decisions (D1, D2) are needed before any code.

**Problem.** `def test_empty(): pass` scans clean, because a `test_*` declaration counts as a fail path. A test whose
body cannot fail verifies nothing.

**Proposal for study.** A new finding for a `test_*` function whose body has no statement that can fail. The open
design questions decide its precision and must be settled in the registration, not after a run: which bodies count
as empty (`pass`, `...`, a docstring only, `return`, only assignments?); whether a test calling a helper counts as
able to fail (it may); how this interacts with VL003 and E16's weakened-assertion fixtures.

**Registration needs**, at minimum: predictions on IE1's `empty_pytest.py` and `blind/test_empty_function.py`
(expected flagged), on IE1's `clean/test_real.py` and the repository's own tests (expected clean), a false-positive
measurement on real test suites, and an anti-vacuity control showing the new rule can return nothing.

## Provenance

Claude (Anthropic, Opus 5.5) wrote these proposals from Putluru Sandeep's IE1 findings → human validation: not
performed → human editing/curation: direction by Chad Holland → human responsibility: Chad Holland. Human review
level: direction only.

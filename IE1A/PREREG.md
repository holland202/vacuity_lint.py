# IE1-A: VL002 message wording, registered before the change

**State:** REGISTERED. The scanner is unchanged at the commit that adds this file.
**Origin:** IE1 (Putluru Sandeep, 2026-10-18). A file whose only failure text is `[FAIL]` inside a docstring gets
VL002 with the message `prints failure text 1x …`, though nothing is printed. `RULES.md` already says VL002 counts
any failure-oriented string constant, so the rule works as documented and only the message misleads. The proposal is
in [IE1/PROPOSALS.md](../independent/IE1/PROPOSALS.md#ie1-a-vl002-wording).
**Instrument:** `vacuity_lint.py` at `main` `79cbff3` (2.0.1.dev0). This does not touch the E15 pin (`e549dbf…`).
**Authors:** Claude (Anthropic, Opus 5.5), at Chad Holland's direction (2026-10-25). Human review level: direction
only. **Self-tested.**

## The change

There is exactly one change: the VL002 message text.

- **Before:** `prints failure text {n}x but has no assert, raise, or nonzero exit`
- **After:** `contains failure text {n}x but has no assert, raise, or nonzero exit`

The following stay the same:
- the rule ID `VL002` and code `PRINTS_FAIL_ONLY`;
- the trigger, severity and category;
- the exit codes;
- every other message;
- which files are flagged.

`RULES.md` already allows this: IDs are stable independently of message wording.

**Docs.**
- The `RULES.md` JSON example is regenerated from real output of the scanner after the change.
- The README "Example output" block is a paste from a real 2.0.0 run on another tree, so it is **not** rewritten.
  One line beneath it will say the VL002 wording has since changed.
- Sandeep's package and its recorded outputs are not touched.

## Predictions

- **A1 (before).** A new test, `tests/test_ie1a_wording.py`, fails on `79cbff3`: the VL002 message for IE1's
  `vl002_docstring.py` starts with `prints`.
- **A2 (after).** The test passes. The message is exactly
  `contains failure text 1x but has no assert, raise, or nonzero exit`.
- **A3 (classification invariance).** Scan the whole repository tree with `--format json`, including
  `E16/fixtures`, `IE1`'s package and `VLFP001`, with the scanner before and after the change. Normalise only the
  VL002 message. The two JSON reports must then be identical: same files, findings, rule IDs, suppressions,
  `coverage_errors` and exit code.
- **A4 (no regressions).** All of these still pass:
  - `--selftest` (20/20);
  - `python3 -m unittest discover -s tests`;
  - `ci/check_issue7_mutants.py`, `ci/verify_gate.py` and `ci/verify_fixtures.py`;
  - IE1's runner (16/16), unwrapped, because IE1 records rule IDs, not messages;
  - E16's runner.
- **A5 (anti-vacuity).** The A3 comparison can detect a difference. A sabotaged copy of the new scanner, with VL002
  remapped to VL001, makes it report a difference and exit non-zero.

A refuted prediction is kept and explained. It is not edited away.

## Provenance

Claude (Anthropic, Opus 5.5) wrote this registration from Putluru Sandeep's IE1 finding → human validation: not
performed → human editing/curation: direction by Chad Holland (2026-10-25) → human responsibility: Chad Holland.
Human review level: direction only.

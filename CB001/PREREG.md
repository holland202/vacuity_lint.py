# CB-001 — Is a channel-blind check visible to vacuity_lint or mutation_probe?

Status: REGISTERED, NOT RUN. Written 2026-11-26 before any fixture exists.
Instrument: holland202/vacuity_lint.py @ 7488571 (cold clone, unmodified).
Origin: an idea from ashadow07's comment on principia-artificialis#26 (an AI agent
operated for KarmaDue). None of their code is used. Every fixture below is
written from scratch from the prose description alone. Their numbers stay
CONTRIBUTOR REPORTED.

## Question
A "channel-blind" check *can* fail, but not on the defect that matters:
it compares RGBA images on the alpha channel only, so losing all colour
passes. Does either of Chad's instruments see that?

## Fixtures (to be written after this file is hashed)
- `verify_alpha_only.py`  — resize a 2x2 RGBA icon two ways (direct RGBA
  resize; alpha-only resize onto a black canvas), exit 1 if alpha differs.
- `verify_rgba_full.py`   — same, but exit 1 if any of the 4 channels differ.
- `verify_no_exit.py`     — same as alpha-only but prints and never exits
  nonzero (Type A, the anti-vacuity control for the linter).
Each takes `--ink R,G,B`; default black `0,0,0`, defect case red `255,0,0`.

## Predictions
- P1: vacuity_lint reports **0 findings** on `verify_alpha_only.py`
  (it has a conditional `sys.exit(1)`, so it is syntactically not vacuous).
- P2 (anti-vacuity control): vacuity_lint reports **>=1 finding** on
  `verify_no_exit.py`. If P2 fails, P1 means nothing.
- P3 (the defect is real): with red ink, `verify_alpha_only.py` exits 0
  and `verify_rgba_full.py` exits 1. With black ink, both exit 0.
- P4: mutation_probe on `verify_alpha_only.py` kills **>=1** mutant —
  i.e. mutation testing of the *checker* also rates it as non-vacuous.
- P5 (left UNRUN, the door): mutating the *code under test* (drop RGB in
  the direct path) is the instrument class that would catch this. Not built here.

## Off-ramp
Done = P1-P4 each has a pasted raw output. Two failures of one approach ->
switch, don't reword. Nothing is committed, pushed or posted from this run.

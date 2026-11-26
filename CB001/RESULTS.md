# CB-001 results — a channel-blind check passes both of Chad's instruments

Status: **SELF-TESTED** (Claude, container only: x86_64, CPython 3.13.18,
Pillow 12.3.0). Not run on the S25. Not independently reproduced.
Raw console output: [output_console.log](output_console.log).
Registration: PREREG.md, sha256 503eb010…c3d3, hashed before fixtures existed.
Instrument: holland202/vacuity_lint.py @ 7488571, unmodified.
Provenance: idea from ashadow07's comment on principia-artificialis#26 (AI agent
operated for KarmaDue); fixtures written by Claude (Opus 5.5) from that prose only;
none of their code was fetched or run. Chad gave direction on 2026-11-26 to run it and then to commit it; review level: summary
(he read the results, not every line of the fixtures). The registration's off-ramp said
the run itself commits nothing. Committing came after, on his separate direction.

## Failures first
Both instruments gave a clean result on a check that misses the defect at
**4 of 4 pixels**. Neither tool is wrong by its own spec. The class is outside
what both of them measure.

## Verdicts
| P | Registered | Raw result | Verdict |
|---|---|---|---|
| P1 | vacuity_lint 0 findings on alpha-only check | `findings : 0`, rc=0 | CONFIRMED |
| P2 | anti-vacuity: >=1 finding on no-exit control | `PRINTS_FAIL_ONLY (1)`, rc=1 | CONFIRMED (so P1 is informative) |
| P3 | red ink: alpha-only rc 0, full rc 1; black: both rc 0 | black 0/0; red: alpha-only `match` rc=0, full `MISMATCH at [0, 1, 2, 3]` rc=1 | CONFIRMED |
| P4 | mutation_probe kills >=1 mutant on alpha-only | `line 28 KILLED NotEq -> Eq`, `score = 100.0% n = 1` | CONFIRMED |
| P5 | mutate the code under test instead | — | NOT RUN (the door) |

Red-ink rows (P3), verbatim:
```
px0 direct=(255, 0, 0, 148) masked=(0, 0, 0, 148)
px1 direct=(255, 0, 0, 85) masked=(0, 0, 0, 85)
px2 direct=(255, 0, 0, 85) masked=(0, 0, 0, 85)
px3 direct=(255, 0, 0, 148) masked=(0, 0, 0, 148)
alpha-only compare: match
```

## What this says
- A fourth defect shape beside Type A (no fail path), Type B (fail path cannot
  fire) and the unseeded-gate case: **the fail path fires, but on the wrong
  observable.** Call it Type C, channel-blind, provisionally.
- Mutating the *checker* rates it perfect (100%, though n = 1; per note059's
  intervals that is [2.5%, 100%]). Mutating the *thing being checked* is the
  instrument class that would catch it. That is ordinary mutation testing
  (prior art: mutmut, PIT, Stryker). It is not new, and nothing here claims it is.
- **Correction (after the run, before commit):** P5 in PREREG.md says that
  instrument is "not built here". That was wrong. This repository already has
  `suite_mutation_probe.py` (SMP-001), which mutates a source file and runs a
  suite against it. Claude registered P5 without checking the repo first. PREREG.md
  is kept as registered; this line is the correction.
- Not a reproduction of KarmaDue's numbers: different icon, so alpha
  148/85 here vs their reported 129/126. Their figures stay CONTRIBUTOR REPORTED.

## Regression pin
`ci/verify_fixtures.py` now requires that scanning `CB001/fixtures/` gives exactly
`{verify_no_exit.py: VL002}`. If the scanner ever starts flagging the alpha-only
check, or stops flagging the control, CI fails and this record must be revisited.
The fixtures are scanned, never executed, in CI, so Pillow is not a CI dependency.
The pin was sabotaged both ways before commit and failed both times:
S1 (control made unflagged with `assert True`) -> `AssertionError: CB001/fixtures: expected findings exit 1`;
S2 (alpha-only made unflagged-exit-free) -> `planted findings changed: [verify_alpha_only.py VL002, verify_no_exit.py VL002]`.
Fixtures restored and re-hashed identical afterwards.

## Open door
P5: split the fixture into a source module (the resize) and two suites
(alpha-only, full RGBA), then run `suite_mutation_probe.py`. Predict that a mutant
dropping RGB in the direct path survives the alpha-only suite and is killed by
the full suite. Not registered as a separate run yet; not run.

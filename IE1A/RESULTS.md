# IE1-A: results (appended after the change; the registration is unchanged)

Registration: [PREREG.md](PREREG.md), committed before the change. The test was committed and seen failing on the
unchanged scanner before the change ([A1 output](results/A1_before_change.txt)). All outputs are in
[results/](results/). Everything here is **self-tested** by its author (Claude, Anthropic, Opus 5.5). Human review
level: direction only.

## Failures first

- **A4 was partly unrunnable as registered.** The registration listed "E16's runner" as a regression check, which was
  a registration error.
  - `E16/run_e16.py` refuses to overwrite `E16/results`.
  - In a throwaway copy it stops at `PRECONDITION FAILED: INCONCLUSIVE`, because it pins the scanner it was executed
    with (`7a5b8d…`).
  - `main` at `79cbff3` already had a different scanner (`20c5e5…`) before this change. So E16's runner cannot check
    any later scanner. That is by design, since E16 was a one-execution experiment.
  - Output: [A4_e16_runner_copy.txt](results/A4_e16_runner_copy.txt). Nothing in E16 was changed.
- **The scanner's module docstring still describes PRINTS_FAIL_ONLY as "prints FAIL/ERROR"** (`vacuity_lint.py`
  line 24). The registration scoped the change to the message only, so this line was left as is. It misleads the same
  way, and it is open.

## Predictions

| ID | Outcome | Evidence |
|---|---|---|
| A1 | HELD | the new test gives `FAILED (failures=2)` on the unchanged scanner |
| A2 | HELD | 2 tests OK; the docstring case and the printed case both get `contains failure text 1x …` |
| A3 | HELD | whole tree, 65 files, 10 findings (3 of them VL002), exit 1 for both scanners; reports identical once the VL002 message is normalised |
| A4 | HELD, except E16 (above) | `--selftest` 20/20; `unittest discover` 60 tests OK; Issue-7 mutants 4/4; fixture controls PASS; gate control PASS; IE1 16 cases, 0 failures |
| A5 | HELD | VL002 remapped to VL001 makes the comparator print `DIFFERENT` and exit 1 |

All of these outputs are in [after_change.txt](results/after_change.txt).

## What changed

- `vacuity_lint.py`: the VL002 message now begins `contains` instead of `prints`. Nothing else in it changed.
- `RULES.md`: the message in the JSON example. Every other value in that example matches the real output.
- `README.md`: one note under the historical 2.0.0 example output, which is otherwise left as pasted.
- New: `tests/test_ie1a_wording.py` and `IE1A/compare_reports.py`.

Sandeep's package is untouched. His runner records rule IDs, not messages, so it still gives 16/16.

## Provenance

Claude (Anthropic, Opus 5.5) made the change, ran every check and wrote this file → human validation: not performed
→ human editing/curation: direction by Chad Holland (2026-10-25) → human responsibility: Chad Holland. Human review
level: direction only.

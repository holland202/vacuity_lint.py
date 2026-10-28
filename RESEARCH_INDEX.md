# Research index

Plain-language map of the research records in this repository. Each folder keeps its own registration and results; nothing here replaces them. Status lines are copied from the records as of 2026-10-27.

| ID | Folder | What it asks | Status |
|---|---|---|---|
| E15 | [E15/](E15/) | Do repositories differ in how much verification-shaped code they contain (author's repos vs sampled repos with and without CI)? Three-arm prevalence study. | Run 2026-10-28 on the re-registration ([RESULTS.md](E15/run/RESULTS.md)): P1 and P2 not confirmed, P3 inconclusive, P4 passed. Author's median 11 vs 3 and 3; the historical gap does not reproduce. Self-tested |
| E16 | [E16/](E16/) | Do `vacuity_lint` and `mutation_probe` catch the test-weakening edits that agentic repair is reported to make? | Run: the two tools together caught 4 of 6 edits ([RESULTS.md](E16/RESULTS.md)) |
| E17 | [E17/](E17/) | Does swarm-verify's `ci` (an outside tool) refuse test-weakening patches it was not built against, in Node and Python? | Run 2026-10-28 ([RESULTS.md](E17/RESULTS.md)): pass withheld on 17 of 18 weakening patches; missed a weakened test helper outside the test files (Node). P4 refuted for Python. Self-tested |
| IE1 | [independent/IE1/](independent/IE1/) | First independent evaluation of the tool, by Putluru Sandeep, with cases he wrote. | Evaluation received 2026-10-18; rerun addendum 2026-10-25 |
| IE1-A | [IE1A/](IE1A/) | Change the VL002 message from "prints" to "contains", since the rule counts any failure string constant. | Results appended ([RESULTS.md](IE1A/RESULTS.md)) |
| IE1-B | [IE1B/](IE1B/) | Should an empty `test_*` function (`def test_x(): pass`) be reported? | REGISTERED, NOT RUN |
| VL-FP-001 | [VLFP001/](VLFP001/) | Four static false passes: a tuple `assert`, `assert True`, a swallowed `AssertionError`, and a `test_` function in a file pytest never collects. `assert True` was kept as a documented blind spot. | Executed, self-tested ([RESULTS.md](VLFP001/RESULTS.md)) |
| VL-FP-002 | [VLFP002/](VLFP002/) | Count `pytest.fail()` as a fail path (a false alarm before the fix). | Executed, self-tested; R1–R5 held ([RESULTS.md](VLFP002/RESULTS.md)) |
| VL-FP-003 | [VLFP003/](VLFP003/) | Stop counting failure words inside tuple/list/set/dict literals (HTTP status-code tables gave false alarms). Trade-off: a failure message stored in a list and printed later is now missed. | Executed, self-tested; R1–R5 held, R6 open; merged before independent review of the trade-off ([RESULTS.md](VLFP003/RESULTS.md)) |
| Issue #7 | [maintenance/](maintenance/) | Engineering maintenance record: scanner coverage errors, non-vacuous CI controls. Not a preregistered experiment. | Record |

"VL-FP" numbers cover scanner precision defects in either direction (false pass or false alarm); each record states its direction. "Self-tested" means the author ran it; only IE1 is independent.

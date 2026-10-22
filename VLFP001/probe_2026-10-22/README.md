# VL-FP probe, 2026-10-22 (the origin of VL-FP-001)

A registered probe ([PREDICTIONS.md](PREDICTIONS.md), SHA-256 `ea318592…fc35`), self-run by Claude (Anthropic, Opus 5.5). It writes small fixture files into a temporary directory, scans them with the scanner given as the argument, and never executes them.

- `probe.py.txt` is the probe script, byte-identical to the one run on 2026-10-22 (SHA-256 `0bf64ae0…df2df`). It is stored with a `.txt` suffix only so that the repository's self-scan does not treat its fixture strings as a vacuous check. Run it with `python3 -I probe.py.txt vacuity_lint.py`.
- `result_main.txt` (`main` at the time) and `result_pr12.txt` (PR #12 head `ce32a82`) are identical: every V row scanned clean.
- `result_after_vlfp001.txt` is this branch. V-A, V-C and V-D are now findings. V-B (`assert True`) stays clean by design (see [../RESULTS.md](../RESULTS.md)). V-E–V-J (coverage, reachability, dead branches) are still open doors.

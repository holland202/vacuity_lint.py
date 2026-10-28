# Reproducing E15

E15's results ([run/RESULTS.md](run/RESULTS.md)) are **self-tested**: everything so far was run by the people who designed it. This page is for anyone willing to check them independently. Your result counts whether or not it matches.

It takes a few minutes on a fast connection (the scan step took 96 seconds in a cloud workspace) and needs no judgement calls. Every step is a command, and the last one tells you whether you got the same answer.

## What you need

- Python 3.10 or newer, `git`, and network access to github.com
- The Python packages `numpy` and `scipy` (`pip install numpy scipy`)
- About 2 GB of free disk space for the downloaded repositories (1.5 GB measured)

## Steps

**1. Get the repository, and confirm that nothing E15 depends on has changed since the results were published** (commit `7b03611`).

```
git clone https://github.com/holland202/vacuity_lint.py e15-check
cd e15-check
git diff --stat 7b036119b3a516a28e0aecf86ba34dc7eea9c895 HEAD -- E15/PREREG_v2.md E15/selection E15/run/run_e15.py E15/run/output
```

The last command should print nothing. If it prints file names, the record has changed since publication; report that.

**2. Run the three self-tests.** These need no network.

```
python E15/selection/select_e15.py --selftest
python E15/run/run_e15.py --selftest
python E15/selection/audit_selection.py E15/selection/run
```

Expected last lines: `6/6 checks passed`, `10/10 checks passed`, `16 passed, 0 failed`.

**3. Re-run the scan.** It uses the committed selection and does not draw a new sample.

```
python E15/run/run_e15.py . ../e15-out ../e15-work
```

It downloads each of the 71 selected repositories at its recorded commit, checks both scanners by sha256, and prints one line per repository. The last line should be:

```
{"P1_C_gt_B": "NOT CONFIRMED", "P2_A_lt_C": "NOT CONFIRMED", "P3_A_equiv_B": "INCONCLUSIVE", "P4_control": "PASS"}
```

**4. Compare your numbers with the published ones.**

```
python E15/run/compare_results.py E15/run/output/results.json ../e15-out/results.json
```

`REPRODUCED` means every verdict and count matches exactly, and every p-value and interval matches to 4 decimal places. `DIFFERS` lists each place it doesn't.

## What this does and doesn't check

- **It checks** that the published scan, statistics and verdicts follow from the committed selection and the pinned scanners, on your machine.
- **It doesn't re-draw the sample.** GitHub's search results change over time, so the sample can't be drawn again. You can audit it instead: `E15/selection/run/raw/search_page_001.txt` is the raw API response, and step 2's audit checks the selection against it.
- **It doesn't check whether "verification-shaped" is a good measure**, or anything else listed under limitations in RESULTS.md. Disagreeing with the design is a valid finding too.

## Reporting back

Please send:

- the output of step 4 (`REPRODUCED` or the `DIFFERS` list)
- your operating system, plus `python --version` and `python -c "import numpy, scipy; print(numpy.__version__, scipy.__version__)"`
- anything that failed or surprised you, including steps that were unclear

Open an issue on this repository, or send it to Chad Holland directly. With your permission, your report will be published in `independent/` under your name, unedited, as the IE1 evaluation was. A result that does not match is published the same way.

## Provenance

Written by Claude (Anthropic, Claude Opus 5.5) on 2026-10-28 at Chad Holland's direction. Before publishing, Claude followed these exact steps from a fresh clone in its own workspace (Linux x86_64, Python 3.13.18, numpy 2.5.3, scipy 1.18.1). Self-tests 6/6, 10/10 and 16/16 passed; the scan's `results.json` and `scans.json` were byte-identical to the committed ones; step 4 printed `REPRODUCED`. That is a check of the instructions on the same platform type as the original run, not an independent reproduction.

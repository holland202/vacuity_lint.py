# E15 v2 — Re-registration: prevalence of verification-shaped code across three repository strata

Status: REGISTERED, NOT RUN
Written: 2026-10-27
Supersedes: [PREREG.md](PREREG.md) (2026-09-08), which was never run and is kept unchanged
Primary instrument: `vacuity_lint.py` from commit `b0db5ac3fc2b20eb16abb6594f1e19746be62650`,
  git blob `14c728c316088ad41d86b1bac913d7dfead8077d`,
  sha256 `a92963c69fa129dbccf94e9672419c2dd2768950d97318183bc8b2820ee815d4`,
  version string `2.0.1.dev0`
Secondary instrument (sensitivity only): `vacuity_lint.py` from commit `e549dbfe9d8c0a03399bef45b66edf7bb6552f58`,
  sha256 `7a5b8d100457128f5cd17c418ea28af480e8c8a488968211508b08b09997292c`
Author: Chad Edward Holland

This document is committed BEFORE any scan is run and before the repository
sample is drawn. Git history is the evidence of that order.

## Why a re-registration

The original registration pinned the scanner at `e549dbf` and forbade
modifying `vacuity_lint.py` before results were published. The scanner was
changed afterwards (v1.1.0, then the Issue #7 repairs and VL-FP-001 to 003)
while E15 remained unrun. [DEVIATIONS.md](DEVIATIONS.md) records that
deviation and left the choice of instrument to the owner. The owner's
decision is recorded in [DECISION_2026-10-27.md](DECISION_2026-10-27.md).

Two facts make a new registration preferable to running the old pin:

1. The later changes move E15's primary outcome, not only its findings.
   [VLFP003/RESULTS.md](../VLFP003/RESULTS.md) records verification-shaped
   counts changing on real repositories (requests 10 → 9, httpx 32 → 31).
   Running `e549dbf` would measure the primary outcome with defects that are
   already known and documented.
2. No E15 data exists. No selection was drawn, no pool page was retrieved,
   and no scan of any pool repository was run under either registration.
   A new registration made now is made in the same epistemic position as
   the original: before any data.

Everything below that is not marked **CHANGED** or **NEW** is carried over
from the original registration word for word in substance. No prediction,
margin, seed, sampling rule, eligibility rule, stratification rule,
exclusion rule, statistic or acceptance band is changed.

## Why this exists (carried over)

A prior measurement compared this author's repositories against ten popular
human-authored ones and reported a large difference in verification-shaped
files per repository. That measurement is NOT reproducible: the ten control
repositories were never named, and the scanner used on them was a separate
reimplementation that was never committed. The figures from it (34.7 and 1.2
files per repository) are recorded here ONLY as the historical observation
that motivated this experiment. They are NOT registered predictions and no
outcome of E15 confirms or refutes them.

E15 does not ask whether the prior result was correct. It asks whether an
independently reproducible procedure finds a difference at all, and if so,
whether repository process explains it.

## The confound this is built to test (carried over)

  (a) authorship — AI-assisted code contains more verification that cannot fail
  (b) process — code without review and CI contains less verification of any kind

The prior design cannot separate them. Three strata can.

## Arms (carried over)

  Arm A   this author's public repositories
  Arm B   sampled public repositories with NO matching CI config path
  Arm C   sampled public repositories WITH a matching CI config path

Authorship cannot be verified from a repository; no arm claims to measure
it. The stratifier detects specific configuration paths, not "has CI". A
repository using GitLab CI, Jenkins, Buildkite or any system not in the path
list is classified Arm B, a known misclassification stated in advance. Paths
may not be added after selection. Arms B and C are drawn as one pool and
split mechanically; arm sizes are whatever the split produces.

## Sampling rule (carried over unchanged)

Pool query, run against the GitHub search API exactly as written:

  language:Python stars:5..50 pushed:>2025-09-08 fork:false archived:false

Sort: stars, descending. Take repositories in returned order.

Eligibility, applied in order, each mechanical:
  1. at least 5 files matching *.py
  2. no more than 2000 files matching *.py
  3. clones successfully at depth 1 within 120 seconds
  4. not owned by holland202

Stratification, after eligibility:
  Arm C if any of .github/workflows/*.yml, .github/workflows/*.yaml,
        .travis.yml, .circleci/config.yml, azure-pipelines.yml exists
  Arm B otherwise

Target: 20 eligible repositories in each of Arm B and Arm C. Continue in
returned order until BOTH reach 20. If either has not reached 20 after 200
eligible repositories, stop and report the shortfall as the result rather
than changing the query.

Arm A is every public repository owned by holland202 that passes
eligibility rules 1-3 on the day of selection. Its size is not chosen.

Provenance: the raw API response for every page consumed is saved to
E15/selection/ with its retrieval timestamp and committed BEFORE any scan
runs. No repository is replaced, skipped or added after selection. A
repository that fails to clone is recorded as an eligibility-3 failure.

The query's date bound (`pushed:>2025-09-08`) is kept as written so the
design does not drift; it now admits roughly 13.5 months of activity rather
than 12. That difference is stated, not corrected.

## Exclusion rules (carried over unchanged)

Excluded from every arm identically:

  conftest.py                 pytest configuration, not a check
  examples/ and example/      demonstration code, not verification
  vendored trees              .venv/, site-packages/, node_modules/, third_party/

**CHANGED (procedure only):** exclusions are applied by removing the
excluded paths from each checkout before any scanner runs, so the primary
and secondary instruments read byte-identical trees. No exclusion may be
added after the scan begins. An unanticipated false-positive class is
reported with its count and left to a separate experiment.

## Primary outcome

  Verification-shaped files per repository.

**CHANGED:** "verification-shaped" is the `verification_shaped` field of the
primary instrument's `--format json` output, run once per repository on the
excluded checkout. The definition is not adjusted.

Unit: the repository. Reported per arm as median with interquartile range,
and as the full distribution.

**NEW — coverage errors.** The primary instrument reports filesystem
coverage errors (files it could not read) in `coverage_errors`. A repository
with any coverage error stays in its arm with the counts the instrument
reports. The number of such repositories per arm, and the number of
unreadable files, are reported. No repository is removed for this reason.

## Secondary outcome (carried over)

  Proportion of repositories containing at least one finding.

Reported with Clopper-Pearson intervals. Expected to be underpowered at
n=20 per stratum, labelled as such in advance, and carries no conclusion on
its own.

## Units (carried over)

Three distinct denominators exist and are not interchangeable: files
scanned, verification-shaped files, findings. Every reported number states
which. No analysis switches between them after the data is seen.

## The comparison procedure (carried over unchanged)

Statistic: two-sided Mann-Whitney U on verification-shaped files per
repository, unit = repository, alpha = 0.05. Reported alongside the median
difference and a 95% bootstrap confidence interval (10,000 resamples,
seed 20260908).

"A difference" means p < 0.05 by that test. Nothing else in this document
means a difference. No other statistic is substituted after seeing data.

## Registered predictions (carried over unchanged)

P1  Arm C has a higher median verification-shaped files per repository
    than Arm B.
P2  Arm A's median is lower than Arm C's median.
P3  Arm A and Arm B are practically equivalent on the primary outcome.
    Quantity: median(Arm A) - median(Arm B), in verification-shaped files
    per repository. Estimated by bootstrap, 10,000 resamples, seed
    20260908, 95% percentile interval.
    P3 CONFIRMED if that interval lies entirely within [-2.0, +2.0].
    P3 REFUTED if that interval lies entirely below -2.0.
    P3 INCONCLUSIVE otherwise, and reported as inconclusive rather than
      as support for either reading.
    Mann-Whitney remains the difference test for P1, P2 and P4 only.
    Margin justification (unchanged): the historical observation implied a
    gap near 33 files per repository; 2.0 sits more than an order of
    magnitude below it. The margin is not adjusted after seeing data.
    P3 is the load-bearing prediction.
P4  ANTI-VACUITY CONTROL. Arm C is split into two halves at random and
    compared against itself with the comparison procedure above, 1000
    times: a generator initialized once with seed 20260908 produces 1000
    DISTINCT half-splits. The proportion of splits returning p < 0.05 is
    recorded.
    P4 PASSES if that proportion falls within [0.02, 0.08].
    P4 FAILS otherwise, and all between-arm comparisons are void.

No prediction registers a numeric target. The procedure is registered; the
numbers fall where they fall. P1-P4 are evaluated on the PRIMARY instrument
only.

## NEW — Instrument-sensitivity analysis (descriptive, no verdicts)

The secondary instrument (`e549dbf`) is run on the same excluded checkouts.
For each arm it reports the median and IQR of verification-shaped files per
repository, and the per-repository difference between the two instruments.

Rules for this analysis, fixed now:
- No prediction is evaluated on it and it cannot change P1-P4.
- If any of P1-P4 would receive a different verdict under the secondary
  instrument, that is reported in plain words as a result about instrument
  sensitivity. It is not reported as a second verdict.
- The secondary instrument has no JSON output. Its verification-shaped count
  is read from its text summary by a parser that is committed, and tested on
  a fixture outside the pool, BEFORE selection. If that parser cannot be
  made to work, this analysis is reported as NOT RUN; the primary analysis
  is unaffected.

## Freeze clause — CHANGED

The original clause froze the repository file, which the project's ongoing
development then broke. This registration freezes the BYTES instead.

At run time the primary instrument is extracted from git blob
`14c728c316088ad41d86b1bac913d7dfead8077d` and its sha256 is checked against
`a92963c69fa129dbccf94e9672419c2dd2768950d97318183bc8b2820ee815d4` before
the first scan; the secondary instrument is checked the same way against its
sha256 above. The checked copies are the only scanners used. Development of
`vacuity_lint.py` on `main` may continue and does not touch E15.

The run is VOIDED, and restarted only under a new registration, if:
- either scanner used does not match its registered sha256;
- the extracted scanner is modified during the run; or
- a defect in the primary instrument is found mid-run. It is not patched
  and continued.

## Known limitations, registered rather than discovered

1. **EXTENDED.** The instrument was developed against Arm A (P13, P14 and
   the original false positives). Since the original registration it was
   also tuned on Putluru Sandeep's independent cases (IE1), on E16's
   fixtures, and on five hand-picked repositories above the pool's star band
   (psf/requests, pallets/flask, pallets/click, Textualize/rich,
   encode/httpx). No repository from the 5..50 star pool has been scanned.
   The detector has still seen Arm A and not Arms B or C. This plausibly
   biases Arm A downward and cannot be removed.
2. Authorship is not measured. No result here supports a claim about AI
   authorship.
3. Python only. Verification that lives in shell or CI YAML is invisible to
   the instrument, which may undercount Arm C.
4. Type B vacuity (a fail path that exists but cannot fire) is not detected.
   Every number here is a Type A count.
5. Stars 5..50 is an arbitrary band. A different band could give a
   different answer.
6. **NEW.** The primary instrument has two documented false-alarm kinds that
   are not fixed ([VLFP003/RESULTS.md](../VLFP003/RESULTS.md)). Kind C,
   benchmark and timing scripts counted as verification-shaped, inflates the
   primary outcome in any repository that has them. It is left in
   deliberately: fixing it before this run would mean changing the
   instrument again with no end point. As a descriptive aid only, the number
   of verification-shaped files whose path contains `bench` is reported per
   arm. It is not used to adjust any count or verdict.
7. **NEW.** VL-FP-003 makes the primary instrument miss a failure message
   stored in a list, tuple, set or dict and printed later, when the file
   name carries no verification hint. That is a false-pass blind spot that
   `e549dbf` did not have. The instrument-sensitivity analysis shows how
   much the two scanners differ but cannot say which is right on any file.

## What voids downstream claims

- P4 fails: all comparisons void.
- Fewer than 20 repositories in either stratum: reported as a shortfall, and
  the primary comparison is reported as underpowered rather than concluded.
- Any freeze-clause violation above.
- Any exclusion rule added after the first scan.

## Left unrun

Whether CI presence or code review is the operative variable in Arm C. They
travel together in public repositories and this design cannot separate them.

VL-FP-003's R6 (frequency of status-code-table false alarms in a random
pool) stays open. It may be measured afterwards on E15's committed
selection, labelled as a secondary look at data already drawn.

## Provenance

Drafted by Claude (Anthropic, Claude Opus 5.5) on 2026-10-27 at Chad
Holland's direction. Chad chose re-registration over running the original
pin, after Claude recommended it. He has not yet reviewed this text line by
line; that review happens on the pull request before it merges. Chad is
responsible for the final registration.

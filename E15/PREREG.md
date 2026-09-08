# E15 — Preregistration: prevalence of verification-shaped code across three repository strata

Status: REGISTERED, NOT RUN
Written: 2026-09-08
Instrument: vacuity_lint.py, pinned at commit e549dbf
Author: Chad Edward Holland

This document is committed BEFORE any scan is run and before the repository
sample is drawn. Git history is the evidence of that order.

## Why this exists

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

## The confound this is built to test

The prior control repositories were popular, reviewed, CI-gated libraries.
Two explanations fit that comparison equally well:

  (a) authorship — AI-assisted code contains more verification that cannot fail
  (b) process — code without review and CI contains less verification of any kind

The prior design cannot separate them. Three strata can.

## Arms — named by what is observable

Authorship cannot be verified from a repository. No arm below claims to
measure it.

  Arm A   this author's public repositories
  Arm B   sampled public repositories with NO matching CI config path
  Arm C   sampled public repositories WITH a matching CI config path

The stratifier detects specific configuration paths, not the abstract
property "has CI". A repository using GitLab CI, Jenkins, Buildkite, or any
system not in the path list below is classified Arm B. That is a known
misclassification, stated in advance. Paths may not be added after selection.

Arms B and C are NOT sampled separately. A single pool is drawn by the rule
below and then split by a mechanical CI check. Arm sizes are whatever the
split produces.

## Sampling rule — fixed before execution

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

Target: 20 eligible repositories in each of Arm B and Arm C. Continue taking
repositories in returned order until BOTH strata reach 20. If either has not
reached 20 after 200 eligible repositories, stop and report the shortfall as
the result rather than changing the query.

Arm A is every public repository owned by holland202 that passes eligibility
rules 1-3. Its size is not chosen.

Provenance: the raw API response for every page consumed is saved to
E15/selection/ with its retrieval timestamp and committed BEFORE any scan
runs. GitHub search results change; the selection event must be
reconstructible.

No repository is replaced, skipped, or added after selection. A repository
that fails to clone is recorded as an eligibility-3 failure, not silently
dropped.

## Exclusion rules — registered in advance

These paths are excluded from every arm identically. All three come from
known false-positive causes in prior runs; registering them now prevents
writing them after seeing results, which would be goalpost-moving:

  conftest.py                 pytest configuration, not a check
  examples/ and example/      demonstration code, not verification
  vendored trees              .venv/, site-packages/, node_modules/, third_party/

No exclusion may be added after the scan begins. If an unanticipated
false-positive class appears, it is reported in the results with its count,
and a separate experiment may address it.

## Primary outcome

  Verification-shaped files per repository.
  (This is the primary OUTCOME MEASURE. Earlier discussion called it a
  "denominator"; that word is reserved below for scan counts.)

Unit: the repository. Reported per arm as median with interquartile range,
and as the full distribution. "Verification-shaped" is whatever
vacuity_lint.py at e549dbf counts as such; the definition is not adjusted.

## Secondary outcome

  Proportion of repositories containing at least one finding.

Reported with Clopper-Pearson intervals. This analysis is expected to be
underpowered at n=20 per stratum and is labelled as such in advance. It does
not carry any conclusion on its own.

## Units — fixed to prevent drift

Three distinct denominators exist and are not interchangeable:
  files scanned, verification-shaped files, findings.
Every reported number states which. No analysis switches between them after
the data is seen.

## The comparison procedure — defined once, used for every comparison

Statistic: two-sided Mann-Whitney U on verification-shaped files per
repository, unit = repository, alpha = 0.05. Reported alongside the median
difference and a 95% bootstrap confidence interval (10,000 resamples,
seed 20260908).

"A difference" means p < 0.05 by that test. Nothing else in this document
means a difference. No other statistic is substituted after seeing data.

## Registered predictions

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

    One quantity, one interval, one margin. An earlier draft confirmed P3
    by an equivalence test on medians and refuted it by Mann-Whitney;
    those are different questions and the branches would not have been
    answering the same one. Mann-Whitney remains the difference test for
    P1, P2 and P4 only.

    Margin justification, fixed before any data: the historical
    observation implied a gap near 33 files per repository. A margin of
    2.0 sits more than an order of magnitude below that, so this test can
    separate "similar" from "an effect of the previously claimed size".
    The margin is not adjusted after seeing data.

    P3 is the load-bearing prediction. If it is CONFIRMED, repository
    process explains the prior result better than authorship does and the
    framing of the earlier work was wrong. Note that failure to find a
    difference is not by itself evidence of equivalence, which is why an
    equivalence test is registered rather than a null result being read
    as sameness.
P4  ANTI-VACUITY CONTROL. Arm C is split into two halves at random and
    compared against itself using the comparison procedure above. This is
    repeated 1000 times: a pseudorandom generator initialized once with
    seed 20260908 produces 1000 DISTINCT half-splits, not one split
    evaluated 1000 times. The proportion of splits returning p < 0.05 is
    recorded.

    P4 PASSES if that proportion falls within the registered acceptance
    band [0.02, 0.08].
    P4 FAILS otherwise, and all between-arm comparisons are void.

    A single split is not a usable control: at alpha = 0.05 it reports a
    difference 5% of the time by construction, so one failure would prove
    nothing and one pass would show nothing. The registered band is the
    nominal false-positive rate with engineering tolerance around
    alpha = 0.05. The band carries no inferential guarantee and is not a
    confidence interval; it is a registered pass/fail threshold chosen
    before running. A rate near zero means the
    procedure cannot detect anything and the between-arm nulls are
    meaningless; a rate well above 0.08 means it manufactures differences
    between halves of one stratum.

No prediction registers a numeric target. The procedure is registered; the
numbers fall where they fall.

## Freeze clause

vacuity_lint.py is pinned at e549dbf and is NOT modified between this commit
and publication of results. If a defect in the tool is found mid-run, the run
is VOIDED and restarted under a new preregistration. It is not patched and
continued.

## Known limitations, registered rather than discovered

1. The instrument was developed against Arm A. P13 and P14 exist because of
   false positives found in this author's own repositories. The detector has
   seen Arm A and has not seen Arms B or C. This asymmetry cannot be removed
   and plausibly biases Arm A downward.
2. Authorship is not measured. Arms B and C may contain AI-assisted code in
   unknown proportion. No result here supports a claim about AI authorship.
3. Python only. A repository whose verification lives in shell or CI YAML is
   invisible to the instrument, which may systematically undercount Arm C.
4. Type B vacuity — a fail path that exists but cannot fire — is not detected
   at all. Every number here is a Type A count.
5. Stars 5..50 is an arbitrary popularity band chosen to avoid both abandoned
   repositories and large maintained projects. A different band could give a
   different answer.

## What voids downstream claims

- P4 fails: all comparisons void.
- Fewer than 20 repositories in either stratum: reported as a shortfall, and
  the primary comparison is reported as underpowered rather than concluded.
- Any modification to vacuity_lint.py between this commit and results.
- Any exclusion rule added after the first scan.

## Left unrun

Whether CI presence or code review is the operative variable in Arm C. They
travel together in public repositories and this design cannot separate them.

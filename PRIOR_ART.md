# Prior art

This tool is not the first to look for checks that pass without being able to fail. This document
names the work that came first, says what overlaps and what does not, and records what was verified
and what was taken on trust. It follows the standard already set in
[REPEATABILITY.md](REPEATABILITY.md): name the established practice, link the existing tools, and
tell the reader when to prefer them.

Nothing in this repository claims the idea is new. This document exists so that nobody has to take
that on faith, and so that [E15](E15/PREREG_v2.md)'s prevalence numbers arrive with the comparison
already made rather than made in response to someone asking.

Checked 2026-11-09.

## The closest existing tool: falsegreen

[falsegreen](https://pypi.org/project/falsegreen/) (Vinicius Queiroz) is a Python static analyser
for tests that pass without protecting anything. Architecturally it is the same shape as this tool:
zero third-party dependencies, a pass over Python's `ast`, and it never imports or runs the code it
inspects. It carries 47 rule codes, including an assertion that never runs, an always-true check, a
swallowed exception, a misspelled mock assertion, and a check in dead code. It has a `--config-audit`
mode that reads `pyproject.toml`, `pytest.ini`, `tox.ini` and `setup.cfg` for configuration that can
hold a suite green, and sibling tools for JS/TS and Robot Framework.

**Prefer falsegreen when the thing you are auditing is a pytest or unittest suite.** It is broader
there, it is grounded in the research below, and it has rules this tool does not have.

### What differs, stated precisely

The unit of analysis is different, and that is the whole of the distinction.

- falsegreen's unit is a **test function inside a framework** — a pytest or unittest test that goes
  green vacuously.
- This tool's unit is a **file that can be run as a check**. `vacuity_lint.py` treats a file as
  verification-shaped "only if it can be RUN as a check", and reports when such a file carries no
  recognised failure mechanism. The motivating cases are a `verify_*.py` that prints
  `MATH IS WRONG - STOP` and exits 0, a `make` target that always succeeds, a CI script nobody
  framed as a test.

Those overlap — an always-true check is in both neighbourhoods — but they are not the same
population, and a file of the second kind is frequently not a test at all.

**This is not a claim that five rules beat forty-seven.** It is a claim that the two tools count
different things. Anyone comparing them on rule count is comparing the wrong axis; anyone comparing
them on findings-per-repository is comparing two different denominators.

## The research this sits downstream of

Secondhand unless marked. These were identified through the citation list of the paper in the next
section and the search that followed; the entries below have **not** been read in full here, and
anyone relying on a characterisation of them should read the source.

- **Rotten green tests** — Delplanque, Ducasse, Polito, Black and Etien, ICSE 2019: tests that pass
  while containing an assertion that never executes, detected with static call-tree analysis plus
  call-site instrumentation. The nearest named concept to this tool's subject.
  [ICSE 2019](https://2019.icse-conferences.org/details/icse-2019-Technical-Papers/43/Rotten-Green-Tests) ·
  [preprint](https://hal.archives-ouvertes.fr/hal-01819302v2)
- **Rotten green tests in Java, Pharo and Python: an empirical study** — Empirical Software
  Engineering, [doi:10.1007/s10664-021-10016-2](https://link.springer.com/10.1007/s10664-021-10016-2).
  Covers Python specifically, and is therefore the most directly relevant prevalence work to E15.
- **RTj** — a Java framework for detecting and refactoring rotten green tests,
  [arXiv:1912.07322](https://ar5iv.labs.arxiv.org/html/1912.07322).
- **Test-smell literature** — the "ugly mirror" or tautological test; the Open Catalog of Test Smells
  lists *Self-Test*. Garousi and Küçük's review is the standard survey.
- **OraclePolish** (Huo and Clause) and **Jahangirova et al.** on oracle false negatives.
- **SonarJS rule S5914**, for assertions with constant conditions.

## Oracles that cannot fail

[arXiv:2608.17214](https://arxiv.org/pdf/2608.17214), *Oracles That Cannot Fail: Anchoring and the
Expectation That Moves With the Fault* (August 2026) is the closest recent work to this tool's
framing. Read in summary here, not in full. It separates **specification-anchored** oracles, whose
expected value is fixed outside the code under test, from **state-anchored** ones that take the
expectation from the code they judge — and argues the latter cannot fail, because a fault that moves
the measurement moves the expectation with it. It proposes a static provenance check over the
import-and-call graph, and measures with mutation testing across 366 mutants in four modules.

Two things follow for this repository.

1. The anchoring distinction is sharper than anything in this tool's rule set, and it names a class
   `vacuity_lint.py` does not detect: a check that *does* have a failure mechanism, but one whose
   expected value comes from the code under test.
2. Its measurement method is mutation testing, which this repository already uses
   (`mutation_probe.py`, `suite_mutation_probe.py`). The two lines agree on method.

## What this means for E15

[E15](E15/PREREG_v2.md) measures verification-shaped files per repository across three strata. It
registers no claim of novelty and this document adds none. Two things are worth stating before its
numbers exist rather than after:

- **E15's outcome is not comparable to a falsegreen finding count.** Different unit, different
  denominator. Any reader who places them side by side is reading a comparison that was never made.
- **The empirical study above measures rotten green tests in Python.** It is the nearest existing
  prevalence result and should be cited when E15 reports, whether or not the numbers resemble each
  other.

Neither point changes a prediction, a margin, a seed, a sampling rule or an acceptance band in
`PREREG_v2.md`. Nothing in the registration is modified by this document.

## AI provenance

Searched, assembled and written by Claude (Anthropic) on owner direction, 2026-11-09. The falsegreen
description comes from its PyPI page, retrieved in that session; the arXiv paper was read in summary,
not in full; the remaining entries are secondhand from citation lists and are marked as such above.
No human has checked these characterisations against their sources. Human validation, editing and
responsibility for the final artifact rest with the owner.

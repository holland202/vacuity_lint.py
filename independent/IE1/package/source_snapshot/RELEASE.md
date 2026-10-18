# Vacuity Lint v1.0.0 — Release candidate and acceptance

**Status:** RELEASE CANDIDATE, NOT PUBLISHED. This document is a release
checklist, not a statement that distribution or independent validation
has occurred. Original scanner: Chad Edward Holland, MIT license.

## Product contract (frozen for 1.0.0)

- Scan local Python files with the existing AST-based heuristic.
- Report recognized missing failure paths and uncollectable test files.
- Exit 0 when Python files were scanned and no findings were detected.
- Exit 1 when any findings were detected.
- Exit 2 when no Python files were scanned.
- Suppress an intentional finding only with its stated reason; show
  suppressed findings separately.
- No network requests, source execution, AI model, or runtime package
  dependencies required by the scanner.
- Known blind spot: this tool does not establish reachability of an
  existing failure branch or prove any test's scientific correctness.

Out of scope: dead-code theorem proving, generalized mutation testing,
AI review, a hosted dashboard, scanning languages other than Python.

## Release acceptance gate (all required)

- [ ] GitHub Actions original gate passes at exact release commit,
      including 20/20 scanner self-tests and the planted-defect test.
- [ ] Release candidate CI builds both **wheel** and **sdist** on
      supported Python versions (3.11, 3.13).
- [ ] **Installed** CLI passes smoke checks on both wheel and sdist:
      version, 20 self-tests, clean=0, defective=1, empty=2, malformed
      Python flagged, and a genuine detection by name.
- [ ] Inspect installed artifacts and confirm no unrelated files,
      secrets, personal data, or unexpected dependency downloads.
- [ ] Review final README, license and scope against a release commit.
- [ ] Obtain owner approval to merge, tag v1.0.0, create GitHub release
      and (separately) upload to PyPI. A named package is NOT evidence
      a PyPI name is available, or that anything has been published.

## Demonstration for maintainers

After `python3 -m pip install .` from an approved release checkout:

```sh
vacuity-lint --selftest
mkdir -p /tmp/vacuity-example
printf "print('[FAIL] detected problem')\\n" > /tmp/vacuity-example/verify_something.py
vacuity-lint /tmp/vacuity-example
echo "exit=$?"
```

The planted script is designed to return a finding and an exit code of 1.
To show a zero-finding case use a separate clean directory containing a
Python file with a real test function and assertion.

## Public communication gate

When verified, publish a small demonstration (before/after) and link to
the exact GitHub tag. Do not claim:
- every broken test is detected;
- all AI-generated tests are broken;
- this provides comprehensive AI agent safety;
- validation beyond listed self-tests and release smoke checks.

Invite maintainers to submit *minimal false-positive/false-negative
examples* through GitHub issues. Disclose that the scanner is an
heuristic and authored/reviewed within the project.

## Useful comparisons

Other static tools examine vacuous assertions and mock misuse; mutmut and
Cosmic Ray run actual mutation tests. Vacuity Lint's distinguishing scope
is detection of *verification-shaped Python scripts with no recognized
failure-reporting route* at near-zero installation cost. Do not market
it as a replacement for those systems.

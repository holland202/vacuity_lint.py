# E18 run notes — 2026-11-11

Environment: Linux x86_64 container, Python 3.13.18. Corpus repos cloned shallow from
github.com/holland202 at the commits pinned in PREREG.md; pins confirmed by
rev-parse before scanning.

## Pre-run instrument correction (before any fixture or corpus run)

The first written classify() recognized assertions only as expression
statements, so `with self.assertRaises(...)` would have been unrecognized
rather than POSITIVE, contradicting the registered table. Corrected before
the first execution: With/AsyncWith context expressions whose attribute name
starts `assert` count as POSITIVE. PREREG.md itself was not modified.

## Why fixtures are never committed

The repository's CI scans its own tree and pins exact planted-fixture
expectations (ci/verify_fixtures.py). Committed E18 fixture files named
test_*.py would enter that scan and perturb expectations unrelated to E18, so
build_fixtures.py writes them to a temporary directory at run time and the
selftest deletes them afterwards.

## Verbatim outputs

All three runs: [output_console.log](output_console.log). The P3 scan reports
one parse error: `independent/IE1/package/independent_cases/defective/test_broken.py`
is a deliberately syntax-broken fixture from the independent evaluation; the
detector reports it rather than skipping it silently.

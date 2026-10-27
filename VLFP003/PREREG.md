# VL-FP-003: failure words inside data tables read as failure messages (static false alarms), registered before the fix

**State:** REGISTERED. The fix is NOT written at the commit that adds this file, and the fixtures have not been run against any scanner version.
**Instrument:** `vacuity_lint.py` at `main` `19eb73e` (2.0.1.dev0). This is an engineering change to the development instrument. It **does not touch the E15 pin** (`e549dbf…`), E15's registration or `E15/DEVIATIONS.md`. Whether E15 keeps its original instrument or gets a new registration remains the owner's decision.
**Authors:** Claude (Anthropic, Opus 5.5), at Chad Holland's direction (2026-10-27). Human review level: direction only. Self-tested.
**Direction of the defect:** false alarm (the scanner reports a finding on code that is not verification), the same direction as VL-FP-002 and the opposite of VL-FP-001.

## Origin (EXPLORATORY, not a registered result)

On 2026-10-27 the scanner at `19eb73e` was run on five large public Python repositories chosen by hand, all above E15's 5–50 star pool so E15's pool was not previewed. Output pasted verbatim from the device run (aarch64, Termux, Python 3.14):

| Repo | python files scanned | verification-shaped | findings |
|---|---|---|---|
| psf/requests | 37 | 10 | 1 |
| pallets/flask | 83 | 30 | 0 |
| pallets/click | 91 | 44 | 1 |
| Textualize/rich | 213 | 69 | 2 |
| encode/httpx | 60 | 32 | 1 |

Hand check of the five findings: 0 true positives.

- **Kind A (this registration), 2 cases, confirmed:** `requests/src/requests/status_codes.py` and `httpx/httpx/_status_codes.py`, both `PRINTS_FAIL_ONLY`, both "contains failure text 3x". `grep -n -i fail` shows the only hits are HTTP status names: `precondition_failed`, `expectation_failed`, `failed_dependency` (requests, lines 67/76/81) and `PRECONDITION_FAILED = 412, "Precondition Failed"`, `EXPECTATION_FAILED`, `FAILED_DEPENDENCY` (httpx, lines 128/133/138). Neither file prints anything. Both are lookup tables.
- **Kind B (not in this registration):** `click/tests/typing/typing_progressbar.py`, `NO_FAIL_PATH`. It uses `assert_type(...)`; click's CI runs a `typing` job and `pyproject.toml` lists `tests/typing` for both type checkers. Real verification, done by an external tool. Deferred: treating `assert_type` as a fail path would create a false *pass* when no type checker is configured, so it needs its own design.
- **Kind C (not in this registration):** `rich/benchmarks/benchmarks.py` and `rich/tools/stress_test_pretty.py`, `NO_FAIL_PATH`. Benchmark and timing scripts, judged from reading only. Deferred: fixing it changes what counts as verification-shaped, which is E15's primary outcome.

## Fixtures

Synthetic, written for this registration; not copied from either project.

**A1 — dict table with an init call (requests-shaped).** File name `status_codes.py`.

```python
_codes = {
    200: ("ok",),
    412: ("precondition_failed", "precondition"),
    417: ("expectation_failed",),
    424: ("failed_dependency", "dependency"),
}
codes = {}


def _init():
    for code, titles in _codes.items():
        for title in titles:
            codes[title] = code


_init()
```

**A2 — enum table with human phrases (httpx-shaped).** File name `_status_codes.py`.

```python
from enum import IntEnum


class codes(IntEnum):
    def __new__(cls, value, phrase=""):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.phrase = phrase
        return obj

    OK = 200, "OK"
    PRECONDITION_FAILED = 412, "Precondition Failed"
    EXPECTATION_FAILED = 417, "Expectation Failed"
    FAILED_DEPENDENCY = 424, "Failed Dependency"


for c in codes:
    setattr(codes, c._name_.lower(), int(c))
```

**Guards — must stay flagged after the fix (anti-vacuity).** Each prints a failure message and exits 0.

G1 `verify_g1.py`:
```python
def check():
    ok = 1 + 1 == 3
    if not ok:
        print("FAILED: arithmetic check")


check()
```

G2 `verify_g2.py`: fixture A1's table followed by G1's body (a table AND a real failure message in one file).

G3 `verify_g3.py` (message held in a variable):
```python
MSG = "FAILED: arithmetic check"


def check():
    if 1 + 1 != 3:
        print(MSG)


check()
```

## Predictions (registered before the fix is written)

- **R1 (unchanged scanner, regression test fails):** at `19eb73e`, A1 and A2 are each reported `PRINTS_FAIL_ONLY`, and G1, G2 and G3 are each reported `PRINTS_FAIL_ONLY`. If a fixture does not reproduce, that is recorded as an R1 failure and fixed by a dated amendment, not by silently editing the fixture until it does.
- **R2 (fix works):** after the fix, A1 and A2 each scan with no finding.
- **R3 (fix is not a mute button):** after the fix, G1, G2 and G3 are each still reported `PRINTS_FAIL_ONLY`. G3 is the hard case. A rule such as "count failure text only inside print/log call arguments" would pass G1 and G2 but miss G3, which would trade a false alarm for a false pass.
- **R4 (no regression):** every existing check passes unchanged: `--selftest`, `tests/test_vlfp001.py`, `tests/test_vlfp002.py`, `mutation_probe.py --selftest`, `provenance_audit.py --selftest`.
- **R5 (real repos):** re-running the fixed scanner on the same five repo checkouts, the requests and httpx findings go to 0. The click and rich findings (kinds B and C) are unchanged, so the total goes from 5 to 3. The verification-shaped counts may change; any change is reported verbatim, not explained away.
- **R6 (OPEN, deliberately not run):** how often kind A occurs in a random Python repository pool. Running it on a 5–50 star pool would preview E15's selection, so it waits for E15's resolution.

## What this registration does not claim

- No false-alarm *rate*. Five hand-picked repositories are not a sample.
- No claim about kinds B or C beyond the hand checks above.
- Nothing about E15's results, instrument or pin.

# E16 results: the two tools together catch 4 of 6 test-weakening edits; 2 slip past both

| | |
|---|---|
| Registration | [`PREREG.md`](PREREG.md) (`3a718bb`) |
| Fixtures and runner | `e7ccfa7`, both committed before the run |
| Execution | One, authorized by Chad Holland on 2026-10-10 |
| Environment | `python3 -I`, Python 3.13.15, Linux container. Not run on the S25 |
| Evidence | `results/run.json`, `results/run.log`; `SHA256SUMS` sha256 `e549adb0…6bdc` |

Written by Claude (Opus 5.5), which also wrote the registration and fixtures. Chad has not reviewed it line by
line. Not independent.

## Failures first: what neither tool catches

- **W1p: a pytest `@pytest.mark.skip` on the only test.** `vacuity_lint` counts any `def test_` as a fail
  path, so a test that pytest will never run looks fine. `mutation_probe` cannot look at a pytest file, because
  it runs targets as scripts. This is the closest analog to the paper's `@Ignore`, and the most common
  real-world form.
- **W4b: weakening to `assert … is not None`.** No finding from the lint. `mutation_probe` has no mutation
  operator for `is` / `is not`, so it reports "could not look" (exit 2). That is honest, but it is not a catch.

## Results (pasted from `results/run.log`)

```
anti-vacuity: W0 clean under both tools: True
VERDICT  lint caught 1/6 ['W3']  |  probe caught 3/6 ['W1', 'W2', 'W4']  |  together 4/6 ['W1', 'W2', 'W3', 'W4']
         14 of 14 cell predictions as registered
```

| ID | Edit | vacuity_lint | mutation_probe |
|---|---|---|---|
| W0 | honest control | clean | 1 mutant KILLED (clean) |
| W1 | test defined but never run | miss | **caught**: `Eq -> NotEq` SURVIVED |
| W1p | `@pytest.mark.skip` | miss | n/a |
| W2 | assertion swallowed by try/except | miss | **caught**: `Eq -> NotEq` SURVIVED |
| W3 | test commented out | **caught**: NO_FAIL_PATH | could not look (0 sites) |
| W4 | `== 5` weakened to `> 0` | miss | **caught**: `Gt -> GtE` SURVIVED |
| W4b | weakened to `is not None` | miss | could not look (0 sites) |

Both self-tests passed first: lint 20/20, probe exit 0.

## Reading

- **The two tools cover different halves.** The lint finds checks with *no* fail path (W3). The probe finds
  checks whose fail path does not *depend* on the logic (W1, W2, W4). Neither alone catches more than half.
- **14 of 14 predictions held, but that is weak evidence.** The predictions came from reading the tools'
  source, so this mostly confirms the reading. It was not an attempt to surprise them.
- **The paper's planned "extra verification step" needs at least two things these tools lack:**
  1. pytest-aware skip detection (skip/xfail markers on otherwise-valid tests);
  2. mutation operators for identity and None checks.

  Both are small, concrete additions. Each would need its own registration.

## What this does not establish

- These are seven hand-built Python analogs, not the paper's real Java edits at Google. It is detection on
  these shapes, not a rate.
- Weakening by intent (reverting the code under test, or a fix that passes but defeats the change's purpose)
  was out of scope and remains undetected by both tools.
- Same author for the tools, the fixtures and the predictions.

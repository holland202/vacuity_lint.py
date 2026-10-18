"""D5 constructed reporting anti-vacuity gate.

No EGRR study seeds, calibration matrices or held-out cases.
"""
import argparse
import math
import sys

from descriptive_scoring import relative_improvement

parser = argparse.ArgumentParser()
parser.add_argument("--sabotage", action="store_true")
args = parser.parse_args()

fixtures = [
    (0.8, 1.0, 0.2),
    (1.0, 1.0, 0.0),
    (1.2, 1.0, -0.2),
]

try:
    records = []
    for cov, mag, expected in fixtures:
        improvement = relative_improvement(cov, mag)

        # Planted reporting defect: silently discard a negative result.
        if args.sabotage and improvement < 0:
            continue

        records.append((improvement, expected))

    if len(records) != len(fixtures):
        raise ValueError("reporting completeness failure")

    for actual, expected in records:
        if not math.isclose(
            actual, expected, rel_tol=0.0, abs_tol=1e-12
        ):
            raise ValueError("incorrect improvement reporting")

    print("GATE: PASS — all positive/zero/negative cases retained")
    sys.exit(0)

except (ValueError, ArithmeticError) as exc:
    print(f"GATE: FAIL — {exc}")
    sys.exit(1)

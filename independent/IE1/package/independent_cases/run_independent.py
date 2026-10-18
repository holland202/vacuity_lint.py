"""Independent black-box cases for the cloned Vacuity Lint CLI."""

import json
from pathlib import Path
import subprocess
import sys


SCANNER = Path(sys.argv[1]).resolve()
ROOT = Path(sys.argv[2]).resolve()


CASES = {
    "clean/test_real.py": (0, set()),
    "clean/verify_assert.py": (0, set()),
    "clean/verify_dynamic_exit.py": (0, set()),
    "clean/ordinary.py": (0, set()),
    "clean/verify_suppressed.py": (0, set()),
    "defective/verify_prints.py": (1, {"VL002"}),
    "defective/test_empty.py": (1, {"VL001", "VL003"}),
    "defective/verify_zero.py": (1, {"VL004"}),
    "defective/test_broken.py": (1, {"VL005"}),
    "blind/verify_unreachable_raise.py": (0, set()),
    "blind/verify_always_assert.py": (0, set()),
    "blind/verify_dead_exit.py": (0, set()),
    "blind/test_empty_function.py": (0, set()),
    "edge/verify_doc_fail.py": (1, {"VL002"}),
    "edge/check_module.py": (1, {"VL001"}),
    "edge/validate_library.py": (0, set()),
}


def scan(relative):
    completed = subprocess.run(
        [sys.executable, str(SCANNER), "--format", "json",
         str(ROOT / relative)],
        text=True, capture_output=True, check=False,
    )
    return completed.returncode, json.loads(completed.stdout)


failures = []
for relative, (expected_rc, expected_rules) in CASES.items():
    actual_rc, report = scan(relative)
    actual_rules = {item["rule_id"] for item in report["findings"]}
    ok = actual_rc == expected_rc and actual_rules == expected_rules
    if relative == "clean/verify_suppressed.py":
        ok = ok and len(report["suppressions"]) == 1
    print(
        f"{'PASS' if ok else 'FAIL'} {relative}: "
        f"exit={actual_rc}, rules={sorted(actual_rules)}, "
        f"status={report['status']}"
    )
    if not ok:
        failures.append(relative)

print(f"\nindependent_cases={len(CASES)} failures={len(failures)}")
if failures:
    print("failed_cases:", ", ".join(failures))
    raise SystemExit(1)

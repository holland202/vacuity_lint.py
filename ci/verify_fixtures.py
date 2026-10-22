#!/usr/bin/env python3
"""Require the existing planted fixture groups to fail for their exact rules."""
import json
from pathlib import Path
import subprocess
import sys

GROUPS = {
    "E16/fixtures": {("E16/fixtures/W3/check_add.py", "VL001")},
    "independent/IE1/package/independent_cases/defective": {
        ("independent/IE1/package/independent_cases/defective/verify_prints.py", "VL002"),
        ("independent/IE1/package/independent_cases/defective/test_empty.py", "VL001"),
        ("independent/IE1/package/independent_cases/defective/test_empty.py", "VL003"),
        ("independent/IE1/package/independent_cases/defective/verify_zero.py", "VL004"),
        ("independent/IE1/package/independent_cases/defective/test_broken.py", "VL005"),
    },
}


def main():
    for root, expected in GROUPS.items():
        result = subprocess.run(
            [sys.executable, "vacuity_lint.py", root, "--format", "json"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        print(root + ": exit=" + str(result.returncode), flush=True)
        print(result.stdout, end="", flush=True)
        if result.returncode != 1 or result.stderr:
            raise AssertionError(f"{root}: expected findings exit 1, not a scan error")
        data = json.loads(result.stdout)
        actual = {(Path(f["path"]).as_posix(), f["rule_id"]) for f in data["findings"]}
        if (data.get("status") != "findings" or data.get("coverage_errors") != []
                or actual != expected):
            raise AssertionError(f"{root}: planted findings changed: {sorted(actual)}")
    print("FIXTURE CONTROLS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())


"""IE1-A: VL002's message says 'contains', not 'prints' (a docstring is not printed).

Registered in IE1A/PREREG.md before the change. Rule ID, trigger and exit code are unchanged.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "vacuity_lint.py"
IE1 = ROOT / "independent" / "IE1" / "package"
EXPECTED = "contains failure text 1x but has no assert, raise, or nonzero exit"


def scan(path):
    done = subprocess.run([sys.executable, str(SCANNER), "--format", "json", str(path)],
                          text=True, capture_output=True, check=False)
    return done.returncode, json.loads(done.stdout)


class IE1AWording(unittest.TestCase):
    def check(self, path):
        rc, report = scan(path)
        self.assertEqual(rc, 1)
        self.assertEqual([(f["rule_id"], f["message"]) for f in report["findings"]], [("VL002", EXPECTED)])

    def test_docstring_case_from_ie1(self):
        self.check(IE1 / "independent_evidence" / "reproductions" / "vl002_docstring.py")

    def test_printed_case_from_ie1(self):
        self.check(IE1 / "independent_cases" / "defective" / "verify_prints.py")


if __name__ == "__main__":
    unittest.main()

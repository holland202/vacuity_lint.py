"""VL-FP-002 regression tests: `pytest.fail()` is a fail path; lookalikes are not.

Registered in VLFP002/PREREG.md (commit 8ecfb02) before this test or the fix existed.
Each case is a fresh `check_case.py` with a __main__ block (so it is verification-shaped), scanned by the
imported scanner. No case file is executed.
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import vacuity_lint as lint

MAIN = '\n\nif __name__ == "__main__":\n    main()\n'

# Expected after the fix: 0 findings.
COUNTED = {
    "C1": 'import pytest\n\n\ndef main():\n    if 2 + 2 != 4:\n        pytest.fail("x")\n' + MAIN,
    "C2": 'import pytest as pt\n\n\ndef main():\n    if 2 + 2 != 4:\n        pt.fail("x")\n' + MAIN,
    "C3": 'from pytest import fail\n\n\ndef main():\n    if 2 + 2 != 4:\n        fail("x")\n' + MAIN,
    "C4": 'from pytest import fail as die\n\n\ndef main():\n    if 2 + 2 != 4:\n        die("x")\n' + MAIN,
}

# Expected before and after the fix: exactly one finding.
NOT_COUNTED = {
    "N1": 'def main():\n    print("checking")\n' + MAIN,
    "N2": 'class Reporter:\n    def fail(self, msg):\n        print(msg)\n\n\ndef main():\n'
          '    obj = Reporter()\n    if 2 + 2 != 4:\n        obj.fail("x")\n' + MAIN,
    "N3": 'import pytest\n\n\nclass Helper:\n    def fail(self, msg):\n        print(msg)\n\n\n'
          'pytest = Helper()\n\n\ndef main():\n    if 2 + 2 != 4:\n        pytest.fail("x")\n' + MAIN,
    "N4": 'def fail(msg):\n    print(msg)\n\n\ndef main():\n    if 2 + 2 != 4:\n        fail("x")\n' + MAIN,
    "N5": 'import pytest\n\n\ndef main():\n    if 2 + 2 != 4:\n        pytest.skip("x")\n' + MAIN,
}


class VLFP002(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vacuity-vlfp002-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.n = 0

    def codes(self, body):
        self.n += 1
        d = self.root / str(self.n)
        d.mkdir()
        p = d / "check_case.py"
        p.write_text(body, encoding="utf-8")
        return [code for code, _ in lint.analyse(str(p))[0]]

    def test_pytest_fail_is_a_fail_path(self):
        for cid, body in COUNTED.items():
            with self.subTest(case=cid):
                self.assertEqual(self.codes(body), [], cid)

    def test_lookalikes_are_not_fail_paths(self):
        for nid, body in NOT_COUNTED.items():
            with self.subTest(case=nid):
                self.assertEqual(len(self.codes(body)), 1, nid)

    def test_mutant_without_recognition_reports_again(self):
        """R3: with the recognition disabled, C1-C4 must be reported again (the test can fail)."""
        with mock.patch.object(lint.Scan, "_is_pytest_fail", lambda self, call: False):
            for cid, body in COUNTED.items():
                with self.subTest(case=cid):
                    self.assertEqual(len(self.codes(body)), 1, cid)


if __name__ == "__main__":
    unittest.main()

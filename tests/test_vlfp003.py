"""VL-FP-003 regression tests: failure words inside data tables are not failure messages.

Registered in VLFP003/PREREG.md (commit 6a38723) before this test or the fix existed.
Fixture text is copied from the registration. Each case is written under its registered file name in a
fresh directory and scanned by the imported scanner. No case file is executed.
"""
import tempfile
import unittest
from pathlib import Path

import vacuity_lint as lint

A1 = '''_codes = {
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
'''

A2 = '''from enum import IntEnum


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
'''

G1 = '''def check():
    ok = 1 + 1 == 3
    if not ok:
        print("FAILED: arithmetic check")


check()
'''

G2 = A1 + "\n\n" + G1

G3 = '''MSG = "FAILED: arithmetic check"


def check():
    if 1 + 1 != 3:
        print(MSG)


check()
'''

# R2: expected after the fix, no finding.
TABLES = {
    "A1": ("status_codes.py", A1),
    "A2": ("_status_codes.py", A2),
}

# R1 and R3: expected before and after the fix, exactly PRINTS_FAIL_ONLY.
GUARDS = {
    "G1": ("verify_g1.py", G1),
    "G2": ("verify_g2.py", G2),
    "G3": ("verify_g3.py", G3),
}


class VLFP003(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vacuity-vlfp003-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.n = 0

    def codes(self, name, body):
        self.n += 1
        d = self.root / str(self.n)
        d.mkdir()
        p = d / name
        p.write_text(body, encoding="utf-8")
        return [code for code, _ in lint.analyse(str(p))[0]]

    def test_tables_are_not_findings(self):
        """R2: a status-code table is not verification and must scan clean."""
        for cid, (name, body) in TABLES.items():
            with self.subTest(case=cid):
                self.assertEqual(self.codes(name, body), [], cid)

    def test_guards_still_flagged(self):
        """R3: real printed failure messages with no fail path must still be reported."""
        for gid, (name, body) in GUARDS.items():
            with self.subTest(case=gid):
                self.assertEqual(self.codes(name, body), ["PRINTS_FAIL_ONLY"], gid)


if __name__ == "__main__":
    unittest.main()

"""VL-FP-001 regression tests: four static false passes and their false-positive guards.

Each case is a fresh file scanned with the imported scanner; no fixture is executed.
Registered in VLFP001/PREREG.md before the fix was written.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import vacuity_lint as lint

ROOT = Path(__file__).resolve().parents[1]

FALSE_PASSES = {
    "V-A": ("verify_tuple.py", 'import sys\nx = 2\nassert (x == 1, "x must be 1")\nprint("[FAIL] would be printed")\n'),
    "V-B": ("verify_true.py", 'print("[FAIL] check failed")\nassert True\n'),
    "V-C": ("verify_swallow.py", 'x = 2\ntry:\n    assert x == 1\nexcept AssertionError:\n    print("[FAIL] x != 1")\n'),
    "V-D": ("verify_testdef.py", 'import sys\ndef test_placeholder():\n    pass\nif __name__ == "__main__":\n'
                                 '    print("[FAIL] check failed")\n    sys.exit(0)\n'),
}

GUARDS = {
    "G1": ("verify_msg.py", 'import sys\nx = len(sys.argv)\nassert x == 1, "x must be 1"\n'),
    "G2": ("verify_paren.py", 'import sys\na = len(sys.argv)\nassert (a == 1)\n'),
    "G3": ("verify_empty_tuple.py", 'print("checking")\nassert ()\n'),
    "G4": ("verify_false.py", 'print("checking")\nassert False\n'),
    "G5": ("verify_reraise.py", 'x = 2\ntry:\n    assert x == 1\nexcept AssertionError:\n    print("[FAIL] x != 1")\n    raise\n'),
    "G6": ("verify_other_exc.py", 'x = 2\ntry:\n    assert x == 1\nexcept ValueError:\n    print("[FAIL] bad value")\n'),
    "G7": ("verify_nested_def.py", 'try:\n    def check(x):\n        assert x == 1\nexcept AssertionError:\n    pass\n'
                                   'print("[FAIL] if check fails")\ncheck(2)\n'),
    "G8": ("test_real_suite.py", 'def test_a():\n    assert 1 + 1 == 2\n'),
    "G9": ("verify_unittest.py", 'import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n'
                                 '        self.assertEqual(1, 1)\nif __name__ == "__main__":\n    unittest.main()\n'),
    "G10": ("verify_called.py", 'def test_value():\n    if 1 + 1 != 2:\n        raise SystemExit(1)\n'
                                'if __name__ == "__main__":\n    test_value()\n'),
}


class VLFP001(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vacuity-vlfp001-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def codes(self, name, contents):
        p = self.root / name
        p.write_text(contents, encoding="utf-8")
        return [code for code, _ in lint.analyse(str(p))[0]]

    def test_false_passes_now_report_a_finding(self):
        for cid, (name, body) in FALSE_PASSES.items():
            with self.subTest(case=cid):
                codes = self.codes(name, body)
                self.assertTrue(set(codes) & {"NO_FAIL_PATH", "PRINTS_FAIL_ONLY"}, f"{cid} scanned clean: {codes}")

    def test_guards_stay_clean(self):
        for gid, (name, body) in GUARDS.items():
            with self.subTest(case=gid):
                self.assertEqual(self.codes(name, body), [], gid)

    def test_cli_exits_one_for_each_false_pass(self):
        for cid, (name, body) in FALSE_PASSES.items():
            with self.subTest(case=cid):
                d = self.root / cid
                d.mkdir()
                (d / name).write_text(body, encoding="utf-8")
                r = subprocess.run([sys.executable, "-I", str(ROOT / "vacuity_lint.py"), str(d)],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()

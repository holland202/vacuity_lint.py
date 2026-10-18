"""Regression tests for v1.0.0 exit and entry-point misclassification.

Each case is a fresh file scanned using the actual imported scanner.
No target fixture is executed.
"""
import tempfile
import unittest
from pathlib import Path

import vacuity_lint as lint


class ExitPrecisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vacuity-exit-precision-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def codes(self, name, contents):
        p = self.root / name
        p.write_text(contents, encoding="utf-8")
        return [code for code, _ in lint.analyse(str(p))[0]]

    def test_raise_systemexit_zero_is_not_failure(self):
        codes = self.codes(
            "verify_syszero.py",
            'if __name__ == "__main__":\n    raise SystemExit(0)\n',
        )
        self.assertEqual(codes, ["ALWAYS_EXITS_ZERO"])

    def test_raise_systemexit_nonzero_is_failure_path(self):
        codes = self.codes(
            "verify_sysone.py",
            'if __name__ == "__main__":\n    raise SystemExit(1)\n',
        )
        self.assertEqual(codes, [])

    def test_os_immediate_exit_nonzero_is_failure_path(self):
        codes = self.codes(
            "verify_osone.py",
            'import os\nif __name__ == "__main__":\n    os._exit(1)\n',
        )
        self.assertEqual(codes, [])

    def test_os_immediate_exit_zero_is_not_failure(self):
        codes = self.codes(
            "verify_oszero.py",
            'import os\nif __name__ == "__main__":\n    os._exit(0)\n',
        )
        self.assertEqual(codes, ["ALWAYS_EXITS_ZERO"])

    def test_sys_exit_zero_has_reachable_classification(self):
        codes = self.codes("verify_zero.py", "import sys\nsys.exit(0)\n")
        self.assertEqual(codes, ["ALWAYS_EXITS_ZERO"])

    def test_printed_failure_preferred_to_generic_zero_class(self):
        codes = self.codes(
            "verify_print_zero.py",
            'import sys\nprint("[FAIL]")\nsys.exit(0)\n',
        )
        self.assertEqual(codes, ["PRINTS_FAIL_ONLY"])

    def test_main_appearing_only_in_comment_is_not_entry_point(self):
        codes = self.codes(
            "verify_library.py",
            '# The term __main__ is documentation, not a guard.\ndef helper():\n    return True\n',
        )
        self.assertEqual(codes, [])

    def test_main_appearing_only_in_docstring_is_not_entry_point(self):
        codes = self.codes(
            "verify_helper.py",
            '"""Documentation: __main__"""\ndef helper():\n    return True\n',
        )
        self.assertEqual(codes, [])

    def test_real_main_guard_is_entry_point(self):
        codes = self.codes(
            "verify_real.py",
            'def main():\n    print("ok")\nif __name__ == "__main__":\n    main()\n',
        )
        self.assertEqual(codes, ["NO_FAIL_PATH"])

    def test_swapped_main_guard_is_entry_point(self):
        codes = self.codes(
            "verify_swapped.py",
            'if "__main__" == __name__:\n    print("ok")\n',
        )
        self.assertEqual(codes, ["NO_FAIL_PATH"])

    def test_ordinary_script_with_zero_exit_not_assumed_verification(self):
        codes = self.codes("ordinary.py", "import sys\nsys.exit(0)\n")
        self.assertEqual(codes, [])

    def test_sys_exit_main_dynamic_remains_recognized(self):
        codes = self.codes(
            "verify_dynamic.py",
            'import sys\ndef main():\n    return 1\nsys.exit(main())\n',
        )
        self.assertEqual(codes, [])

    def test_unittest_class_test_detection_unchanged(self):
        codes = self.codes(
            "test_example.py",
            'import unittest\nclass TestExample(unittest.TestCase):\n'
            '    def test_pass(self):\n        self.assertTrue(True)\n',
        )
        self.assertEqual(codes, [])


if __name__ == "__main__":
    unittest.main()

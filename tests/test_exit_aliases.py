"""Simple imported exits are recognized; ambiguous shadowed calls are not."""
from pathlib import Path
import tempfile
import unittest

import vacuity_lint as lint


class ExitAliasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vacuity-alias-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "verify_alias.py"

    def codes(self, source):
        self.path.write_text(source, encoding="utf-8")
        return [code for code, _ in lint.analyse(self.path)[0]]

    def test_simple_imported_nonzero_exits_and_abort(self):
        cases = (
            "import sys as s\ns.exit(1)\n",
            "from sys import exit as bye\nbye(1)\n",
            "import os as system\nsystem._exit(1)\n",
            "from os import _exit as bye\nbye(1)\n",
            "import os\nos.abort()\n",
            "import os as system\nsystem.abort()\n",
            "from os import abort as stop\nstop()\n",
        )
        for source in cases:
            with self.subTest(source=source):
                self.assertEqual(self.codes('print("[FAIL]")\n' + source), [])

    def test_aliased_zero_exits_do_not_hide_findings(self):
        for source in ("import sys as s\ns.exit(0)\n",
                       "from sys import exit as bye\nbye(None)\n",
                       "from os import _exit as bye\nbye(0)\n"):
            with self.subTest(source=source):
                self.assertEqual(self.codes('print("[FAIL]")\n' + source),
                                 ["PRINTS_FAIL_ONLY"])

    def test_rebinding_alias_to_noop_is_not_a_failure_path(self):
        source = ('import sys as s\nclass Noop:\n'
                  '    def exit(self, code):\n        pass\n'
                  's = Noop()\nprint("[FAIL]")\n'
                  's.exit(1)\n')
        self.assertEqual(self.codes(source), ["PRINTS_FAIL_ONLY"])

    def test_imported_function_shadowed_by_assignment_is_not_recognized(self):
        source = ('from sys import exit as bye\nbye = lambda code: None\n'
                  'print("[FAIL]")\nbye(1)\n')
        self.assertEqual(self.codes(source), ["PRINTS_FAIL_ONLY"])

    def test_parameter_shadowing_is_conservatively_rejected(self):
        source = ('import sys as s\ndef check(s):\n    s.exit(1)\n'
                  'print("[FAIL]")\n')
        self.assertEqual(self.codes(source), ["PRINTS_FAIL_ONLY"])

    def test_unrelated_exit_method_is_not_a_stdlib_exit(self):
        self.assertEqual(self.codes('print("[FAIL]")\nservice.exit(1)\n'),
                         ["PRINTS_FAIL_ONLY"])

    def test_other_module_import_cannot_claim_sys_alias(self):
        source = 'import other as s\nprint("[FAIL]")\ns.exit(1)\n'
        self.assertEqual(self.codes(source), ["PRINTS_FAIL_ONLY"])

    def test_function_named_exit_shadows_builtin(self):
        source = 'def exit(code):\n    return None\nprint("[FAIL]")\nexit(1)\n'
        self.assertEqual(self.codes(source), ["PRINTS_FAIL_ONLY"])

    def test_float_zero_is_not_process_exit_zero(self):
        self.assertEqual(self.codes('import sys\nprint("[FAIL]")\nsys.exit(0.0)\n'), [])

    def test_multiple_systemexit_arguments_are_nonzero(self):
        self.assertEqual(self.codes('print("[FAIL]")\nraise SystemExit(0, 1)\n'), [])


if __name__ == "__main__":
    unittest.main()


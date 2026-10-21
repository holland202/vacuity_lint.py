"""Issue #7 regressions. Target source is parsed, never executed."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import vacuity_lint as lint

SCANNER = Path(lint.__file__).resolve()


class ScanIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vacuity-integrity-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, source):
        target = self.root / name
        target.write_text(source, encoding="utf-8")
        return target

    def invoke(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SCANNER), *map(str, arguments)],
            capture_output=True, text=True, timeout=15, check=False,
        )

    def local_json(self, *arguments):
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", [str(SCANNER), "--format", "json",
                                             *map(str, arguments)]):
            with contextlib.redirect_stdout(stdout):
                code = lint.main()
        return code, json.loads(stdout.getvalue())

    def test_mixed_missing_root_never_clean_in_either_order_or_format(self):
        valid = self.write("ordinary.py", "value = 1\n")
        missing = self.root / "missing"
        for roots in ((valid, missing), (missing, valid)):
            for output in ("text", "json"):
                with self.subTest(roots=roots, output=output):
                    result = self.invoke(*roots, "--format", output)
                    self.assertEqual(result.returncode, 2, result.stdout)
                    if output == "json":
                        data = json.loads(result.stdout)
                        self.assertEqual(data["status"], "analysis_error")
                        self.assertEqual(data["files_scanned"], 1)
                        self.assertEqual(data["coverage_errors"][0]["path"], str(missing))
                        self.assertEqual(result.stderr, "")
                    else:
                        self.assertIn(str(missing), result.stderr)
                        self.assertNotIn("no vacuous verification found", result.stdout)

    def test_coverage_error_takes_precedence_without_hiding_findings(self):
        bad = self.write("verify_bad.py", 'print("[FAIL]")\n')
        result = self.invoke(bad, self.root / "missing", "--format", "json")
        self.assertEqual(result.returncode, 2)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "analysis_error")
        self.assertEqual([f["rule_id"] for f in data["findings"]], ["VL002"])
        self.assertEqual(len(data["coverage_errors"]), 1)

    def test_all_missing_roots_are_reported(self):
        paths = (self.root / "missing-a", self.root / "missing-b")
        result = self.invoke(*paths, "--format", "json")
        self.assertEqual(result.returncode, 2)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "analysis_error")
        self.assertEqual({e["path"] for e in data["coverage_errors"]}, set(map(str, paths)))

    def test_empty_existing_directory_retains_no_python_status(self):
        result = self.invoke(self.root, "--format", "json")
        self.assertEqual(result.returncode, 2)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "no_python_files")
        self.assertEqual(data["coverage_errors"], [])

    def test_directory_traversal_error_is_not_silently_skipped(self):
        denied = str(self.root / "denied")

        def broken_walk(root, **options):
            options["onerror"](PermissionError(13, "Permission denied", denied))
            yield  # keep this an iterator, as os.walk is

        with mock.patch.object(lint.os, "walk", broken_walk):
            code, data = self.local_json(self.root)
        self.assertEqual(code, 2)
        self.assertEqual(data["status"], "analysis_error")
        self.assertIn(denied, data["coverage_errors"][0]["message"])

    def test_file_disappearing_after_enumeration_is_coverage_error(self):
        vanished = str(self.root / "vanished.py")
        with mock.patch.object(lint, "walk", return_value=iter([vanished])):
            code, data = self.local_json(self.root)
        self.assertEqual(code, 2)
        self.assertEqual(data["coverage_errors"][0]["path"], vanished)

    @unittest.skipUnless(os.name == "posix", "requires POSIX directory permissions")
    def test_actual_unreadable_subtree_reports_coverage_error(self):
        # Use a disposable scanner copy so a dropped-privilege child does not
        # need access to this checkout or any other host file.
        self.root.chmod(0o755)
        scanner = self.root / "scanner.py"
        scanner.write_bytes(SCANNER.read_bytes())
        scanner.chmod(0o644)
        tree = self.root / "tree"
        tree.mkdir(mode=0o755)
        (tree / "ordinary.py").write_text("value = 1\n", encoding="utf-8")
        denied = tree / "denied"
        denied.mkdir()
        (denied / "hidden.py").write_text("value = 2\n", encoding="utf-8")
        denied.chmod(0)

        def drop_privileges():
            os.setgroups([])
            os.setgid(65534)
            os.setuid(65534)

        try:
            try:
                result = subprocess.run(
                    [sys.executable, str(scanner), str(tree), "--format", "json"],
                    capture_output=True, text=True, timeout=15, check=False,
                    preexec_fn=drop_privileges if os.geteuid() == 0 else None,
                )
            except subprocess.SubprocessError as exc:
                self.skipTest(f"cannot create unprivileged child: {exc}")
            self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "analysis_error")
            self.assertTrue(any(str(denied) in e["message"] for e in data["coverage_errors"]))
        finally:
            denied.chmod(0o700)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires a FIFO-capable platform")
    def test_special_root_is_rejected_without_opening_it(self):
        fifo = self.root / "fifo"
        os.mkfifo(fifo)
        result = self.invoke(fifo, "--format", "json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "analysis_error")

    def test_suppression_markers_inside_literals_do_not_suppress(self):
        sources = (
            'marker = "# vacuity-lint: intentional - copied example"\n',
            '"""# vacuity-lint: intentional - copied docstring"""\n',
            'marker = """first\n# vacuity-lint: intentional - multiline\nlast"""\n',
        )
        for prefix in sources:
            with self.subTest(prefix=prefix):
                path = self.write("verify_literal.py", prefix + 'print("[FAIL]")\n')
                findings, scan = lint.analyse(path)
                self.assertEqual([code for code, _ in findings], ["PRINTS_FAIL_ONLY"])
                self.assertIsNone(scan.suppressed)

    def test_real_comment_suppression_retains_exact_reason(self):
        for source in (
            '# vacuity-lint: intentional - advisory only\nprint("[FAIL]")\n',
            'print("[FAIL]")  # vacuity-lint: intentional - advisory only\n',
        ):
            with self.subTest(source=source):
                path = self.write("verify_comment.py", source)
                findings, scan = lint.analyse(path)
                self.assertEqual(findings, [])
                self.assertEqual(scan.suppressed, "advisory only")

    def test_reasonless_comment_cannot_suppress(self):
        path = self.write("verify_comment.py",
                          '# vacuity-lint: intentional -   \nprint("[FAIL]")\n')
        findings, scan = lint.analyse(path)
        self.assertEqual([code for code, _ in findings], ["PRINTS_FAIL_ONLY"])
        self.assertIsNone(scan.suppressed)

    def test_systemexit_zero_forms_cannot_supply_fail_path(self):
        for statement in ("raise SystemExit", "raise SystemExit()",
                          "raise SystemExit(0)", "raise SystemExit(None)"):
            with self.subTest(statement=statement):
                path = self.write("verify_exit.py", 'print("[FAIL]")\n' + statement + "\n")
                findings, _ = lint.analyse(path)
                self.assertEqual([code for code, _ in findings], ["PRINTS_FAIL_ONLY"])

    def test_nonzero_dynamic_and_ordinary_raises_remain_fail_paths(self):
        for statement in ("raise SystemExit(1)", "raise SystemExit(code)",
                          'raise RuntimeError("bad")'):
            with self.subTest(statement=statement):
                path = self.write("verify_exit.py", 'print("[FAIL]")\n' + statement + "\n")
                self.assertEqual(lint.analyse(path)[0], [])


if __name__ == "__main__":
    unittest.main()


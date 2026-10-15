"""Contract tests for the v1.1.0 JSON output, version and legacy CLI."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCANNER = Path(__file__).resolve().parents[1] / "vacuity_lint.py"


class JSONContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vacuity-json-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make(self, name, content):
        target = self.root / name
        target.write_text(content, encoding="utf-8")
        return target

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCANNER), *(str(a) for a in args)],
            text=True, capture_output=True, timeout=30, check=False
        )

    def test_version(self):
        r = self.run_cli("--version")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "vacuity_lint.py 1.1.0")

    def test_legacy_text_mode_and_code_unchanged(self):
        file = self.make("verify_bad.py", 'print("[FAIL] but still 0")\n')
        r = self.run_cli(file)
        self.assertEqual(r.returncode, 1)
        self.assertIn("PRINTS_FAIL_ONLY", r.stdout)
        self.assertFalse(r.stdout.startswith("{"))

    def test_clean_json(self):
        file = self.make("test_working.py", "def test_ok():\n    assert 2 + 2 == 4\n")
        r = self.run_cli(file, "--format", "json")
        self.assertEqual(r.returncode, 0, r.stderr)
        v = json.loads(r.stdout)
        self.assertEqual(v["status"], "clean")
        self.assertEqual(v["tool"], "vacuity-lint")
        self.assertEqual(v["version"], "1.1.0")
        self.assertEqual(v["files_scanned"], 1)
        self.assertEqual(v["findings"], [])
        self.assertEqual(v["suppressions"], [])

    def test_real_finding_metadata_and_no_invented_location(self):
        file = self.make("verify_bad.py", 'print("[FAIL] but no exit")\n')
        r = self.run_cli("--format", "json", file)
        self.assertEqual(r.returncode, 1)
        f = json.loads(r.stdout)["findings"]
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["rule_id"], "VL002")
        self.assertEqual(f[0]["rule"], "PRINTS_FAIL_ONLY")
        self.assertEqual(f[0]["severity"], "warning")
        self.assertEqual(f[0]["category"], "heuristic")
        self.assertFalse(f[0]["suppressed"])
        self.assertNotIn("line", f[0])
        self.assertEqual(f[0]["path"], str(file))
        self.assertEqual(r.stderr, "")

    def test_empty_input_is_json_but_exit_two(self):
        r = self.run_cli(self.root, "--format", "json")
        self.assertEqual(r.returncode, 2)
        v = json.loads(r.stdout)
        self.assertEqual(v["status"], "no_python_files")
        self.assertEqual(v["files_scanned"], 0)
        self.assertEqual(v["findings"], [])

    def test_suppression_explained_and_visible(self):
        f = self.make("verify_thermal.py",
                      '# vacuity-lint: intentional - hardware-only advisory check\n'
                      'print("[FAIL] sensor unavailable")\n')
        r = self.run_cli("--format", "json", f)
        self.assertEqual(r.returncode, 0)
        v = json.loads(r.stdout)
        self.assertEqual(v["findings"], [])
        self.assertEqual(v["suppressions"][0]["reason"], "hardware-only advisory check")
        self.assertEqual(v["suppressions"][0]["path"], str(f))
        self.assertTrue(v["suppressions"][0]["suppressed"])

    def test_bare_suppression_does_not_hide(self):
        f = self.make("verify_bare.py",
                      '# vacuity-lint: intentional\nprint("[FAIL]")\n')
        r = self.run_cli("--format", "json", f)
        self.assertEqual(r.returncode, 1)
        v = json.loads(r.stdout)
        self.assertEqual(len(v["findings"]), 1)
        self.assertEqual(v["suppressions"], [])

    def test_unparseable_is_analysis_error(self):
        f = self.make("test_malformed.py", "def broken(:\n")
        r = self.run_cli("--format", "json", f)
        self.assertEqual(r.returncode, 1)
        v = json.loads(r.stdout)["findings"][0]
        self.assertEqual((v["rule"], v["rule_id"], v["severity"], v["category"]),
                         ("UNPARSEABLE", "VL005", "error", "analysis_error"))

    def test_zero_exit_rule(self):
        f = self.make("verify_success_only.py",
                      'import sys\nif __name__ == "__main__":\n    sys.exit(0)\n')
        r = self.run_cli("--format", "json", f)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)["findings"][0]["rule_id"], "VL004")

    def test_multiple_paths_and_quiet_json(self):
        clean = self.make("ordinary.py", "x = 1\n")
        bad = self.make("test_empty.py", "print('checking')\n")
        r = self.run_cli(clean, bad, "--format", "json", "--quiet")
        self.assertEqual(r.returncode, 1)
        v = json.loads(r.stdout)
        self.assertEqual(v["files_scanned"], 2)
        self.assertIn("VL003", [f["rule_id"] for f in v["findings"]])
        self.assertIn("VL001", [f["rule_id"] for f in v["findings"]])

    def test_invalid_format_refused(self):
        r = self.run_cli("--format", "sarif")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(r.stdout.strip())


if __name__ == "__main__":
    unittest.main()

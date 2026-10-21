"""Black-box sabotage controls for the CI gate instrument itself."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "ci" / "verify_gate.py"
SCANNER = ROOT / "vacuity_lint.py"


class GateControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vacuity-control-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tree = self.root / "scan"
        self.tree.mkdir()
        (self.tree / "ordinary.py").write_text("value = 1\n", encoding="utf-8")

    def run_control(self, scanner):
        result = subprocess.run(
            [sys.executable, str(CONTROL), str(scanner), str(self.tree),
             "--evidence-dir", str(self.root / "evidence")],
            capture_output=True, text=True, timeout=20, check=False,
        )
        self.assertEqual(list(self.tree.glob("vacuity-gate-*")), [],
                         "probe directory must be cleaned even on failure")
        return result

    def fake(self, name, source):
        path = self.root / name
        path.write_text(source, encoding="utf-8")
        return path

    def test_real_scanner_accepts_clean_planted_clean_and_retains_raw_exits(self):
        result = self.run_control(SCANNER)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("GATE CONTROL PASS", result.stdout)
        self.assertEqual(
            [(self.root / "evidence" / (stage + ".exit")).read_text().strip()
             for stage in ("clean-before", "planted", "clean-after")],
            ["0", "1", "0"],
        )

    def test_always_zero_is_rejected_at_planted_exit(self):
        payload = {"status": "clean", "files_scanned": 1, "findings": [],
                   "coverage_errors": []}
        fake = self.fake("always_zero.py", "import json\nprint(" + repr(json.dumps(payload)) + ")\n")
        result = self.run_control(fake)
        self.assertEqual(result.returncode, 1)
        self.assertIn("planted: expected exit 1, got 0", result.stderr)

    def test_always_one_and_always_two_are_rejected_before_planting(self):
        for code in (1, 2):
            with self.subTest(code=code):
                fake = self.fake("constant.py", f"raise SystemExit({code})\n")
                result = self.run_control(fake)
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"clean-before: expected exit 0, got {code}", result.stderr)

    def test_unrelated_finding_cannot_satisfy_planted_control(self):
        source = """import json, sys
from pathlib import Path
root = Path(sys.argv[1])
probe = list(root.rglob("verify_gate_probe.py"))
data = {"status": "findings" if probe else "clean",
        "files_scanned": 2 if probe else 1, "coverage_errors": [],
        "findings": ([{"path": str(root / "unrelated.py"),
                      "rule_id": "VL002", "rule": "PRINTS_FAIL_ONLY",
                      "category": "heuristic"}] if probe else [])}
print(json.dumps(data))
raise SystemExit(1 if probe else 0)
"""
        result = self.run_control(self.fake("unrelated.py", source))
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected only VL002 for the planted probe", result.stderr)

    def test_error_exit_is_not_a_detected_defect(self):
        source = """import json, sys
from pathlib import Path
probe = list(Path(sys.argv[1]).rglob("verify_gate_probe.py"))
print(json.dumps({"status": "clean", "files_scanned": 1,
                  "findings": [], "coverage_errors": []}))
raise SystemExit(2 if probe else 0)
"""
        result = self.run_control(self.fake("error_on_probe.py", source))
        self.assertEqual(result.returncode, 1)
        self.assertIn("planted: expected exit 1, got 2", result.stderr)

    def test_zero_exit_with_invalid_json_is_rejected(self):
        result = self.run_control(self.fake("invalid_json.py", 'print("clean")\n'))
        self.assertEqual(result.returncode, 1)
        self.assertIn("did not return valid JSON", result.stderr)

    def test_preexisting_defect_cannot_mask_probe(self):
        (self.tree / "verify_other.py").write_text('print("[FAIL]")\n', encoding="utf-8")
        result = self.run_control(SCANNER)
        self.assertEqual(result.returncode, 1)
        self.assertIn("clean-before: expected exit 0, got 1", result.stderr)


if __name__ == "__main__":
    unittest.main()


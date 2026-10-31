"""SMP-001 P4/P5: suite_mutation_probe.py leaves the suite's working directory as it found it."""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "SMP001" / "demo"


def tree(d):
    return {str(p.relative_to(d)): (hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "dir")
            for p in sorted(Path(d).rglob("*"))}


class CleanupTests(unittest.TestCase):
    def run_probe(self, cwd, suite):
        return subprocess.run([sys.executable, str(ROOT / "suite_mutation_probe.py"), "--source", str(Path(cwd) / "governor.py"),
                               "--suite", f"{sys.executable} {suite}", "--cwd", str(cwd), "--timeout", "60"],
                              capture_output=True, text=True, timeout=600)

    def test_suite_cwd_is_byte_identical_after_both_demo_runs(self):
        for suite, want in (("suite_real.py", 0), ("suite_theatre.py", 1)):
            with tempfile.TemporaryDirectory() as td:
                shutil.copytree(DEMO, td, dirs_exist_ok=True)
                before = tree(td)
                r = self.run_probe(td, suite)
                self.assertEqual(r.returncode, want, suite + r.stdout[-400:] + r.stderr[-400:])
                self.assertEqual(tree(td), before, suite)

    def test_preexisting_smp_cov_directory_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as td:
            shutil.copytree(DEMO, td, dirs_exist_ok=True)
            mine = Path(td) / "_smp_cov" / "mine.txt"
            mine.parent.mkdir()
            mine.write_text("user data")
            self.run_probe(td, "suite_real.py")
            self.assertEqual(mine.read_text(), "user data")


if __name__ == "__main__":
    unittest.main()

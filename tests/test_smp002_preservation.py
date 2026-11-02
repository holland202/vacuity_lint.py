"""SMP-002 (findings by ChatGPT, review on draft PR #30): the probe never destroys user files.

A1 existing _smp_cov files, A2 an existing <source>.mutbak, A3 a CRLF source restored byte for byte.
C2' replaces ChatGPT's C2 control (which edited a line the fix removed): with the cleanup line sabotaged,
the probe's own instrumentation directory must be found left behind in TMPDIR, so the test can fail."""
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


def run(probe, cwd, tmpdir, suite="suite_real.py"):
    env = dict(os.environ, TMPDIR=str(tmpdir))
    return subprocess.run([sys.executable, str(probe), "--source", str(Path(cwd) / "governor.py"),
                           "--suite", f"{sys.executable} {suite}", "--cwd", str(cwd), "--timeout", "60"],
                          capture_output=True, text=True, timeout=600, env=env)


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.work = self.td / "demo"
        shutil.copytree(DEMO, self.work)
        self.tmp = self.td / "tmp"
        self.tmp.mkdir()

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_a1_existing_smp_cov_files_untouched(self):
        for name, data in {"sitecustomize.py": b"# mine\n", "executed.txt": b"log\n", "attach.log": b"a\n",
                           "bin/python3": b"#!/bin/sh\n", "mine.txt": b"x\n"}.items():
            p = self.work / "_smp_cov" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        before = tree(self.work)
        r = run(ROOT / "suite_mutation_probe.py", self.work, self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        self.assertEqual(tree(self.work), before)

    def test_a2_existing_backup_untouched(self):
        (self.work / "governor.py.mutbak").write_bytes(b"user backup\n")
        before = tree(self.work)
        r = run(ROOT / "suite_mutation_probe.py", self.work, self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        self.assertEqual(tree(self.work), before)

    def test_a3_crlf_source_restored_byte_for_byte(self):
        g = self.work / "governor.py"
        g.write_bytes(g.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        before = tree(self.work)
        r = run(ROOT / "suite_mutation_probe.py", self.work, self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        self.assertEqual(tree(self.work), before)

    def test_no_instrumentation_left_in_tmpdir(self):
        run(ROOT / "suite_mutation_probe.py", self.work, self.tmp)
        self.assertEqual([p.name for p in self.tmp.iterdir() if p.name.startswith("smp_cov_")], [])

    def test_c2_prime_sabotaged_cleanup_is_caught(self):
        tool = self.td / "tool"
        tool.mkdir()
        for n in ("suite_mutation_probe.py", "mutation_probe.py"):
            shutil.copy2(ROOT / n, tool / n)
        p = tool / "suite_mutation_probe.py"
        old = "        shutil.rmtree(stub_dir, ignore_errors=True)  # SMP-001 P4 / SMP-002 A1: always ours"
        text = p.read_text()
        self.assertEqual(text.count(old), 1)
        p.write_text(text.replace(old, "        pass  # SABOTAGE"))
        run(p, self.work, self.tmp)
        leaked = [q for q in self.tmp.iterdir() if q.name.startswith("smp_cov_")]
        self.assertTrue(leaked, "sabotaged cleanup left nothing behind: this test could not see the failure")


if __name__ == "__main__":
    unittest.main()

"""Deterministic verdict controls and process-lifecycle regressions."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import repeatability_probe as repeat

SCRIPT = Path(repeat.__file__).resolve()
COUNTER = (
    "from pathlib import Path\n"
    "p = Path('counter')\n"
    "n = int(p.read_text()) if p.exists() else 0\n"
    "p.write_text(str(n + 1))\n"
)


@unittest.skipUnless(os.name == "posix", "probe requires POSIX process groups")
class RepeatabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="repeatability-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def probe(self, source, **options):
        return repeat.probe([sys.executable, "-c", source], cwd=self.root,
                            **({"runs": 3, "timeout": 10} | options))

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              cwd=self.root, capture_output=True, text=True,
                              timeout=20, check=False)

    def test_consistent_pass_records_command_and_exact_output_hashes(self):
        report = self.probe("import sys; print('ok'); sys.stderr.buffer.write(b'\\xff')")
        self.assertEqual((report["status"], report["exit_code"]), ("consistent_pass", 0))
        self.assertEqual(report["completed_runs"], 3)
        self.assertEqual(report["observed_exit_codes"], [0])
        self.assertFalse(report["output_varies"])
        self.assertEqual(report["cwd"], str(self.root))
        self.assertEqual(report["command"][:2], [sys.executable, "-c"])
        self.assertEqual(report["instrument_sha256"], hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
        for attempt in report["attempts"]:
            self.assertEqual(attempt["stdout"]["sha256"], hashlib.sha256(b"ok\n").hexdigest())
            self.assertEqual(attempt["stderr"]["sha256"], hashlib.sha256(b"\xff").hexdigest())
            self.assertEqual(attempt["stderr"]["bytes"], 1)

    def test_consistent_nonzero_exit_never_becomes_a_pass(self):
        report = self.probe("raise SystemExit(7)")
        self.assertEqual((report["status"], report["exit_code"]), ("consistent_fail", 1))
        self.assertEqual(report["observed_exit_codes"], [7])
        self.assertEqual([a["exit_code"] for a in report["attempts"]], [7, 7, 7])

    def test_signal_exit_is_a_failure(self):
        report = self.probe("import os, signal; os.kill(os.getpid(), signal.SIGTERM)", runs=2)
        self.assertEqual((report["status"], report["exit_code"]), ("consistent_fail", 1))
        self.assertEqual(report["observed_exit_codes"], [-signal.SIGTERM])

    def test_identical_output_cannot_hide_changing_verdicts(self):
        report = self.probe(COUNTER + "raise SystemExit(n % 2)", runs=4)
        self.assertEqual((report["status"], report["exit_code"]), ("inconsistent", 1))
        self.assertEqual([a["exit_code"] for a in report["attempts"]], [0, 1, 0, 1])
        self.assertEqual(report["completed_runs"], 4)
        self.assertFalse(report["output_varies"])
        self.assertEqual((self.root / "counter").read_text(), "4")

    def test_different_nonzero_codes_are_still_recorded_as_inconsistent(self):
        report = self.probe(COUNTER + "raise SystemExit(2 + n % 2)")
        self.assertEqual(report["status"], "inconsistent")
        self.assertEqual(report["observed_exit_codes"], [2, 3])
        self.assertEqual(report["exit_code"], 1)

    def test_changing_output_is_separate_from_a_passing_verdict(self):
        report = self.probe(COUNTER + "print(n)")
        self.assertEqual((report["status"], report["exit_code"]), ("consistent_pass", 0))
        self.assertTrue(report["output_varies"])
        self.assertEqual(report["output_variants"], 3)

    def test_stderr_and_bytes_beyond_the_preview_affect_output_identity(self):
        source = COUNTER + (
            "import sys\n"
            f"sys.stdout.buffer.write(b'x' * {repeat.PREVIEW_BYTES + 20})\n"
            "sys.stderr.buffer.write(b'x' * 5000 + bytes([n]))\n"
        )
        report = self.probe(source, runs=2)
        first, second = report["attempts"]
        self.assertEqual(first["stderr"]["preview"], second["stderr"]["preview"])
        self.assertNotEqual(first["stderr"]["sha256"], second["stderr"]["sha256"])
        self.assertEqual(first["stderr"]["bytes"], 5001)
        self.assertTrue(first["stderr"]["preview_truncated"])
        self.assertTrue(first["stdout"]["preview_truncated"])
        self.assertLessEqual(len(first["stdout"]["preview"].encode()), repeat.PREVIEW_BYTES)
        self.assertTrue(report["output_varies"])

    def test_timeout_is_incomplete_and_keeps_partial_output(self):
        report = self.probe("import time; print('started', flush=True); time.sleep(60)", timeout=1)
        self.assertEqual((report["status"], report["exit_code"]), ("incomplete", 2))
        self.assertEqual(report["completed_runs"], 0)
        self.assertEqual(len(report["attempts"]), 1)
        attempt = report["attempts"][0]
        self.assertEqual(attempt["kind"], "timeout")
        self.assertIsNone(attempt["exit_code"])
        self.assertEqual(attempt["process_returncode"], -signal.SIGKILL)
        self.assertIn("started", attempt["stdout"]["preview"])
        self.assertIsNone(report["output_varies"])

    def test_partial_measurement_keeps_earlier_completed_evidence(self):
        report = self.probe(COUNTER + "import time\nif n: time.sleep(60)\n", timeout=1)
        self.assertEqual((report["status"], report["exit_code"]), ("incomplete", 2))
        self.assertEqual(report["completed_runs"], 1)
        self.assertEqual(report["observed_exit_codes"], [0])
        self.assertEqual([a["kind"] for a in report["attempts"]], ["completed", "timeout"])

    def test_missing_executable_or_cwd_is_incomplete(self):
        for command, cwd in (([str(self.root / "missing")], self.root),
                             ([sys.executable, "-c", "pass"], self.root / "missing")):
            with self.subTest(command=command, cwd=cwd):
                report = repeat.probe(command, cwd=cwd, runs=2)
                self.assertEqual((report["status"], report["exit_code"]), ("incomplete", 2))
                self.assertEqual(report["attempts"][0]["kind"], "spawn_error")
                self.assertEqual(report["completed_runs"], 0)

    def test_capture_and_cleanup_errors_cannot_report_a_completed_pass(self):
        for target in ("tempfile.TemporaryFile", "_cleanup"):
            with self.subTest(target=target), mock.patch(
                    "repeatability_probe." + target, side_effect=OSError("planted I/O failure")):
                report = self.probe("pass")
                self.assertEqual((report["status"], report["exit_code"]), ("incomplete", 2))
                self.assertEqual(report["completed_runs"], 0)
                self.assertIn("planted I/O failure", report["attempts"][0]["error"])

    def test_interruption_cleans_up_and_reports_incomplete(self):
        original_wait = subprocess.Popen.wait
        interrupted = False

        def wait_once(process, *args, **kwargs):
            nonlocal interrupted
            if not interrupted:
                interrupted = True
                raise KeyboardInterrupt
            return original_wait(process, *args, **kwargs)

        with mock.patch.object(subprocess.Popen, "wait", new=wait_once):
            report = self.probe("import time; time.sleep(60)")
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["attempts"][0]["kind"], "interrupted")
        self.assertEqual(report["attempts"][0]["process_returncode"], -signal.SIGKILL)

        with mock.patch.object(repeat, "_fingerprint", side_effect=KeyboardInterrupt):
            report = self.probe("pass")
        self.assertEqual((report["status"], report["exit_code"]), ("incomplete", 2))
        self.assertEqual(report["attempts"][0]["kind"], "interrupted")
        self.assertEqual(report["attempts"][0]["process_returncode"], 0)

    @unittest.skipUnless(sys.platform.startswith("linux"), "checks Linux process state")
    def test_background_child_is_stopped_after_completion_and_timeout(self):
        for timeout_case in (False, True):
            with self.subTest(timeout=timeout_case):
                source = (
                    "import subprocess, sys, time\n"
                    "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                    "print(child.pid, flush=True)\n"
                ) + ("time.sleep(60)\n" if timeout_case else "")
                report = self.probe(source, runs=2, timeout=1)
                for attempt in report["attempts"]:
                    pid = int(attempt["stdout"]["preview"].strip())
                    deadline = time.monotonic() + 2
                    while True:
                        try:
                            state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
                        except (FileNotFoundError, ProcessLookupError):
                            break
                        if state == "Z":  # dead; only the host's reaper remains responsible
                            break
                        if time.monotonic() >= deadline:
                            os.kill(pid, signal.SIGKILL)
                            self.fail("probe left its command's background child running")
                        time.sleep(0.01)

    def test_invalid_arguments_are_refused_before_execution(self):
        for options in ({"runs": 0}, {"runs": 1}, {"runs": True}, {"runs": 2.5},
                        {"timeout": 0}, {"timeout": -1}, {"timeout": float("nan")},
                        {"timeout": float("inf")}, {"timeout": True}, {"timeout": None},
                        {"timeout": "1"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.probe("pass", **options)
        for command in ([], "python -c pass", [""], ["bad\x00program"]):
            with self.subTest(command=command), self.assertRaises(ValueError):
                repeat.probe(command)
        result = self.cli("--runs", 1, "--", sys.executable, "-c", "pass")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_json_never_interprets_arguments_as_shell_code(self):
        literal = "literal; $(touch should-not-exist) & > ignored"
        result = self.cli("--runs", 2, "--format", "json", "--", sys.executable,
                          "-c", "import sys; print(sys.argv[1])", literal)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["command"][-1], literal)
        self.assertEqual(report["attempts"][0]["stdout"]["preview"], literal + "\n")
        self.assertEqual(set(self.root.iterdir()), set())

    def test_cli_nonzero_and_text_contract(self):
        failed = self.cli("--runs", 2, "--format", "json", "--", sys.executable,
                          "-c", "raise SystemExit(7)")
        self.assertEqual(failed.returncode, 1)
        self.assertEqual(json.loads(failed.stdout)["status"], "consistent_fail")
        passed = self.cli("--runs", 2, "--", sys.executable, "-c", "pass")
        self.assertEqual(passed.returncode, 0)
        self.assertIn("consistent_pass", passed.stdout)
        self.assertIn("determinism is not established", passed.stdout)
        missing = self.cli("--runs", 2, "--format", "json", "--", self.root / "missing")
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(json.loads(missing.stdout)["status"], "incomplete")

    def test_selftest_passes_and_rejects_a_constant_pass_classifier(self):
        for sabotage in (False, True):
            output = io.StringIO()
            patch = mock.patch.object(repeat, "_classify", return_value=("consistent_pass", 0))
            with (patch if sabotage else contextlib.nullcontext()), contextlib.redirect_stdout(output):
                code = repeat.selftest()
            self.assertEqual(code, 1 if sabotage else 0)
            self.assertIn("[FAIL]" if sabotage else "6/6 controls passed", output.getvalue())


if __name__ == "__main__":
    unittest.main()

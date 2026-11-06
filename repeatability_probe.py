#!/usr/bin/env python3
"""Repeat a command and retain every observed verdict. Python 3.10+, POSIX.

Exit 0: all requested executions completed with exit 0.
Exit 1: executions completed, with inconsistent exits or a consistent failure.
Exit 2: measurement incomplete (timeout, interruption, launch/capture/cleanup error).

This executes the supplied command, with its normal filesystem/network effects.
It neither seeds the command nor resets its state. See REPEATABILITY.md.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time

__version__ = "0.1.0.dev0"
PREVIEW_BYTES = 4096


def _fingerprint(stream):
    """Hash a fixed snapshot in chunks; previews are explicitly incomplete."""
    remaining = os.fstat(stream.fileno()).st_size
    stream.seek(0)
    digest = hashlib.sha256()
    preview = bytearray()
    size = 0
    while remaining:
        chunk = stream.read(min(65536, remaining))
        if not chunk:
            raise OSError("capture shortened while reading its snapshot")
        digest.update(chunk)
        preview.extend(chunk[:max(0, PREVIEW_BYTES - len(preview))])
        size += len(chunk)
        remaining -= len(chunk)
    return {
        "sha256": digest.hexdigest(),
        "bytes": size,
        "preview": preview.decode("utf-8", errors="replace"),
        "preview_truncated": size > PREVIEW_BYTES,
    }


def _cleanup(process):
    # start_new_session=True gives this attempt its own POSIX process group.
    # Clean up background children even when the top-level command already exited.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def _attempt(command, cwd, timeout, index):
    started = time.monotonic()
    result = {"index": index, "kind": "completed", "exit_code": None,
              "process_returncode": None, "stdout": None, "stderr": None}
    process = None
    try:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            try:
                process = subprocess.Popen(
                    command, cwd=cwd, stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, start_new_session=True,
                )
                result["exit_code"] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                result["kind"] = "timeout"
                result["error"] = f"command exceeded {timeout:g} seconds"
            except KeyboardInterrupt:
                result["kind"] = "interrupted"
                result["error"] = "interrupted by user"
            except (OSError, ValueError) as exc:
                result["kind"] = "spawn_error"
                result["error"] = str(exc)
            finally:
                if process is not None:
                    try:
                        _cleanup(process)
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        result["kind"] = "cleanup_error"
                        result["error"] = str(exc)
                        result["exit_code"] = None
                    result["process_returncode"] = process.returncode
            result["stdout"] = _fingerprint(stdout)
            result["stderr"] = _fingerprint(stderr)
    except OSError as exc:
        result["kind"] = "capture_error"
        result["error"] = str(exc)
        result["exit_code"] = None
    except KeyboardInterrupt:
        result["kind"] = "interrupted"
        result["error"] = "interrupted while capturing or cleaning up"
        result["exit_code"] = None
        if process is not None:
            try:
                _cleanup(process)
            except (OSError, subprocess.TimeoutExpired) as exc:
                result["kind"] = "cleanup_error"
                result["error"] = str(exc)
            result["process_returncode"] = process.returncode
    result["elapsed_seconds"] = round(time.monotonic() - started, 6)
    return result


def _classify(attempts, requested):
    if len(attempts) != requested or any(a["kind"] != "completed" for a in attempts):
        return "incomplete", 2
    codes = {a["exit_code"] for a in attempts}
    if len(codes) > 1:
        return "inconsistent", 1
    return ("consistent_pass", 0) if codes == {0} else ("consistent_fail", 1)


def probe(command, *, runs=5, timeout=30.0, cwd=None):
    """Run an explicit argv repeatedly, without a shell, seeding or state reset."""
    if os.name != "posix":
        raise ValueError("this version requires POSIX process groups")
    if isinstance(command, (str, bytes)):
        raise ValueError("command must be an argv sequence, not a shell string")
    command = [os.fspath(part) for part in command]
    if (not command or not command[0]
            or any(not isinstance(p, str) or "\x00" in p for p in command)):
        raise ValueError("command requires non-NUL text arguments and a program name")
    if isinstance(runs, bool) or not isinstance(runs, int) or runs < 2:
        raise ValueError("runs must be an integer of at least 2")
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("timeout must be finite and greater than zero")
    directory = os.path.abspath(os.path.expanduser(os.fspath(cwd) if cwd is not None else os.getcwd()))
    report = {
        "schema_version": 1,
        "tool": "repeatability-probe",
        "version": __version__,
        "instrument_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "python": {"executable": sys.executable, "version": platform.python_version()},
        "platform": platform.system(),
        "command": command,
        "cwd": directory,
        "requested_runs": runs,
        "timeout_seconds": timeout,
        "attempts": [],
    }
    for index in range(1, runs + 1):
        attempt = _attempt(command, directory, timeout, index)
        report["attempts"].append(attempt)
        if attempt["kind"] != "completed":
            break
    completed = [a for a in report["attempts"] if a["kind"] == "completed"]
    signatures = {(a["stdout"]["sha256"], a["stderr"]["sha256"]) for a in completed}
    report["completed_runs"] = len(completed)
    report["observed_exit_codes"] = sorted({a["exit_code"] for a in completed})
    report["output_variants"] = len(signatures)
    report["output_varies"] = len(signatures) > 1 if completed else None
    report["status"], report["exit_code"] = _classify(report["attempts"], runs)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    return report


def selftest():
    """Deterministic controls; they measure the instrument, not a real project."""
    counter = (
        "from pathlib import Path\n"
        "p = Path('counter')\n"
        "n = int(p.read_text()) if p.exists() else 0\n"
        "p.write_text(str(n + 1))\n"
    )
    cases = (
        ("consistent pass", "print('fixed')", "consistent_pass", 0, False),
        ("consistent failure", "raise SystemExit(7)", "consistent_fail", 1, False),
        ("changing verdict, identical output", counter + "raise SystemExit(n % 2)",
         "inconsistent", 1, False),
        ("changing output, passing verdict", counter + "print(n)", "consistent_pass", 0, True),
        ("timeout is incomplete", "import time; time.sleep(60)", "incomplete", 2, None),
    )
    passed = 0
    with tempfile.TemporaryDirectory(prefix="repeatability-selftest-") as temp:
        root = Path(temp)
        for index, (label, source, status, exit_code, output_varies) in enumerate(cases):
            directory = root / str(index)
            directory.mkdir()
            report = probe([sys.executable, "-c", source], runs=4,
                           timeout=0.15 if status == "incomplete" else 10, cwd=directory)
            ok = (report["status"] == status and report["exit_code"] == exit_code
                  and report["output_varies"] == output_varies)
            print(f"[{'PASS' if ok else 'FAIL'}] {label}")
            passed += ok
        report = probe([str(root / "missing-command")], runs=2, cwd=root)
        ok = (report["status"] == "incomplete" and report["exit_code"] == 2
              and report["completed_runs"] == 0)
        print(f"[{'PASS' if ok else 'FAIL'}] missing command is incomplete")
        passed += ok
    print(f"{passed}/6 controls passed")
    return 0 if passed == 6 else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=30.0, help="seconds per execution")
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="-- PROGRAM [ARG ...]")
    args = parser.parse_args(argv)
    if args.selftest:
        if args.command:
            parser.error("--selftest does not accept a command")
        if os.name != "posix":
            parser.error("this version requires POSIX process groups")
        return selftest()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        report = probe(command, runs=args.runs, timeout=args.timeout, cwd=args.cwd)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"status: {report['status']}")
        print(f"completed: {report['completed_runs']}/{report['requested_runs']}")
        print(f"exit codes: {report['observed_exit_codes']}")
        print(f"output variants: {report['output_variants']}")
        for attempt in report["attempts"]:
            print(f"  run {attempt['index']}: {attempt['kind']}, exit={attempt['exit_code']}")
            if "error" in attempt:
                print(f"    {attempt['error']}")
        if report["status"] == "consistent_pass":
            print("No inconsistency observed in these runs; determinism is not established.")
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())

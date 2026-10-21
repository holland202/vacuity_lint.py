#!/usr/bin/env python3
"""Check the repository gate with clean, planted, then clean JSON scans.

Only a disposable copy of the scan tree is modified. The scanner is executed;
the planted source is never executed.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


class GateCheckError(RuntimeError):
    pass


def verify_gate(scanner, scan_root, evidence_dir=None):
    scanner = Path(scanner).resolve(strict=True)
    scan_root = Path(scan_root).resolve(strict=True)
    if not scan_root.is_dir():
        raise GateCheckError("scan root must be a disposable directory")
    if evidence_dir is not None:
        evidence_dir = Path(evidence_dir)
        evidence_dir.mkdir(parents=True, exist_ok=True)

    def scan(stage, expected_exit):
        command = [sys.executable, str(scanner), str(scan_root), "--format", "json"]
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=30, check=False)
        if evidence_dir is not None:
            (evidence_dir / (stage + ".stdout")).write_text(result.stdout, encoding="utf-8")
            (evidence_dir / (stage + ".stderr")).write_text(result.stderr, encoding="utf-8")
            (evidence_dir / (stage + ".exit")).write_text(
                str(result.returncode) + "\n", encoding="utf-8")
        print(stage + ": exit=" + str(result.returncode), flush=True)
        print(result.stdout, end="", flush=True)
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr, flush=True)
        if result.returncode != expected_exit:
            raise GateCheckError(
                f"{stage}: expected exit {expected_exit}, got {result.returncode}")
        try:
            data = json.loads(result.stdout)
        except (ValueError, TypeError) as exc:
            raise GateCheckError(f"{stage}: scanner did not return valid JSON") from exc
        if not isinstance(data, dict):
            raise GateCheckError(f"{stage}: JSON must be an object")
        if (data.get("coverage_errors") != [] or result.stderr
                or type(data.get("files_scanned")) is not int
                or data["files_scanned"] < 1
                or not isinstance(data.get("findings"), list)):
            raise GateCheckError(f"{stage}: incomplete or malformed scan")
        return data

    def clean(stage, count=None):
        data = scan(stage, 0)
        if (data.get("status") != "clean" or data["findings"]
                or (count is not None and data["files_scanned"] != count)):
            raise GateCheckError(f"{stage}: expected the original clean tree")
        return data["files_scanned"]

    with tempfile.TemporaryDirectory(prefix="vacuity-gate-", dir=scan_root) as temp:
        probe = Path(temp) / "verify_gate_probe.py"
        original_count = clean("clean-before")
        probe.write_text(
            'import sys\nprint("[FAIL] planted gate control")\nsys.exit(0)\n',
            encoding="utf-8",
        )
        data = scan("planted", 1)
        expected = data["findings"]
        if not (data.get("status") == "findings"
                and data["files_scanned"] == original_count + 1
                and len(expected) == 1 and isinstance(expected[0], dict)
                and expected[0].get("path") == str(probe)
                and expected[0].get("rule_id") == "VL002"
                and expected[0].get("rule") == "PRINTS_FAIL_ONLY"
                and expected[0].get("category") == "heuristic"):
            raise GateCheckError("planted: expected only VL002 for the planted probe")
        probe.unlink()
        clean("clean-after", original_count)
    print("GATE CONTROL PASS: clean -> sole intended VL002 -> clean", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scanner", type=Path)
    parser.add_argument("scan_root", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    try:
        verify_gate(args.scanner, args.scan_root, args.evidence_dir)
    except (GateCheckError, OSError, subprocess.TimeoutExpired) as exc:
        print("GATE CONTROL FAIL: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())


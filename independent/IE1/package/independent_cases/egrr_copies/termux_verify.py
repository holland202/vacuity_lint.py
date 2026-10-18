"""Constructed-only EGRR-DESC-001 verification package.

Designed for Android Termux and usable for explicitly labelled local checks.
It does not generate either reserved research seed block or execute a study.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import subprocess
import sys


INSTRUMENT_COMMIT = "29c63fe399fa1cbc45974717b8de14a1cd989401"
PACKAGE_BASE_COMMIT = "4fd0e25416673e7d75f9dd61f9fe396e043e4fe4"
EXPECTED_SOURCES = {
    "experiments/egrr_issue28/canonical_evidence.py":
        "c5de9fb5b42b6d6fd103f75b0020bd82195e6f667bf788b9b7237f5a463e9ceb",
    "experiments/egrr_issue28/case_envelope.py":
        "bcb4c5289c75a571446a90a35cc021129a49b7d241ece51a5caae2582526fbd5",
    "experiments/egrr_issue28/covariance_float16.py":
        "623fac46c82edff9373e4f17f17e4809b5fcc47daf1a0c9bb5ac7af2bae707e4",
    "experiments/egrr_issue28/descriptive_case_record.py":
        "522168fb522e40dbe00e5f4659fd5022c123122c5f74b1d02f8ae39a67f5f189",
    "experiments/egrr_issue28/descriptive_scoring.py":
        "79b1140dfeb1c0ad717ca3de735a3986285dc0c3b56704211369c83861abae04",
    "experiments/egrr_issue28/egrr.py":
        "a73f6b6d8e970995cf2c89d6f6c417d11a27e8776a7a42acbdf121b1dd17e756",
    "experiments/egrr_issue28/packing.py":
        "c1fa507ab1ec4b7e493ed5e388bdf31a9bc8a235e8ca5aaaab082ddb36f44097",
    "experiments/egrr_issue28/storage.py":
        "1a20b6ec271ec4bb7d47e3d0f65a284559efc83ab2f0a1457e09dbd349b4f6f1",
    "experiments/egrr_issue28/verified_aggregate.py":
        "3384fe449c3482b1e86af321674c8ac119714e0cdaf1f95246a013eadbacb69b",
}
PACKAGE_FILES = (
    "reproducibility/egrr_desc_001_termux/README.md",
    "reproducibility/egrr_desc_001_termux/noise_probe.py",
    "reproducibility/egrr_desc_001_termux/registered_fixture_gate.py",
    "reproducibility/egrr_desc_001_termux/requirements-termux.txt",
    "reproducibility/egrr_desc_001_termux/test_termux_verify.py",
    "reproducibility/egrr_desc_001_termux/termux_verify.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_version(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def git(root, *args):
    completed = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def run_check(
    name, command, cwd, expected_exit, raw_dir,
    *, expected_stdout=None, stdout_contains=None, expected_stderr="",
    stderr_contains=None,
):
    completed = subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, check=False
    )
    stdout_path = raw_dir / f"{name}.stdout.txt"
    stderr_path = raw_dir / f"{name}.stderr.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    conditions = {"exit_matches": completed.returncode == expected_exit}
    if stderr_contains is not None:
        conditions["stderr_contains"] = stderr_contains in completed.stderr
    else:
        conditions["stderr_matches"] = completed.stderr == expected_stderr
    if expected_stdout is not None:
        conditions["stdout_matches"] = completed.stdout == expected_stdout
    if stdout_contains is not None:
        conditions["stdout_contains"] = stdout_contains in completed.stdout
    return {
        "name": name,
        "command": command,
        "expected_exit": expected_exit,
        "actual_exit": completed.returncode,
        "expected_stdout": expected_stdout,
        "stdout_contains": stdout_contains,
        "expected_stderr": expected_stderr,
        "stderr_contains": stderr_contains,
        "conditions": conditions,
        "passed": all(conditions.values()),
        "stdout_file": f"raw/{name}.stdout.txt",
        "stdout_sha256": sha256(stdout_path),
        "stderr_file": f"raw/{name}.stderr.txt",
        "stderr_sha256": sha256(stderr_path),
    }


def write_summary(summary, output_dir):
    pretty = json.dumps(summary, sort_keys=True, indent=2) + "\n"
    compact = json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n"
    (output_dir / "termux-verification.json").write_text(
        pretty, encoding="utf-8"
    )
    (output_dir / "termux_verify.stdout.txt").write_text(
        compact, encoding="utf-8"
    )
    (output_dir / "termux_verify.stderr.txt").write_text("", encoding="utf-8")
    print(compact, end="")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path,
        help="directory for JSON and raw output (default: package directory)",
    )
    args = parser.parse_args()
    package_dir = Path(__file__).resolve().parent
    root = package_dir.parents[1]
    egrr_dir = root / "experiments" / "egrr_issue28"
    output_dir = args.output_dir.resolve() if args.output_dir else package_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    _, checkout_commit, _ = git(root, "rev-parse", "HEAD")
    _, status, _ = git(root, "status", "--porcelain")
    identities = {}
    identity_errors = []
    if status:
        identity_errors.append("checkout is not clean")
    for relative, expected in EXPECTED_SOURCES.items():
        path = root / relative
        if not path.is_file():
            identity_errors.append(f"missing source: {relative}")
            continue
        actual = sha256(path)
        identities[relative] = actual
        if actual != expected:
            identity_errors.append(f"source SHA-256 mismatch: {relative}")

    package_identities = {
        relative: sha256(root / relative)
        for relative in PACKAGE_FILES
        if (root / relative).is_file()
    }
    summary = {
        "schema": "EGRR-DESC-001-VERIFY-2",
        "scientific_status": "DRAFT / NOT FROZEN / NOT RUN",
        "instrument_commit": INSTRUMENT_COMMIT,
        "verification_package_base_commit": PACKAGE_BASE_COMMIT,
        "checkout_commit": checkout_commit,
        "checkout_clean": not bool(status),
        "checkout_status": status.splitlines(),
        "source_sha256_expected": EXPECTED_SOURCES,
        "source_sha256_actual": identities,
        "package_sha256_actual": package_identities,
        "identity_errors": identity_errors,
        "identity_ok": not identity_errors,
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy_version": package_version("numpy"),
        "pytest_version": package_version("pytest"),
        "checks": [],
    }

    # Source identity is a veto: do not execute tests against unpinned code.
    if identity_errors:
        summary["verification_ok"] = False
        write_summary(summary, output_dir)
        return 1

    checks = [
        run_check(
            "sabotage_oracle_control",
            [sys.executable, "-m", "pytest", "-q",
             str(package_dir / "test_termux_verify.py")],
            root, 0, raw_dir, stdout_contains="1 passed",
        ),
        run_check(
            "malformed_registration",
            [sys.executable, "-m", "pytest", "-q",
             "test_verified_aggregate.py::VerifiedAggregateTests::test_invalid_registration_inputs_fail_closed"],
            egrr_dir, 0, raw_dir, stdout_contains="1 passed",
        ),
        run_check(
            "full_egrr_regression",
            [sys.executable, "-m", "unittest", "discover", "-s", ".",
             "-p", "test_*.py", "-q"],
            egrr_dir, 0, raw_dir,
            stdout_contains="PASS: six-arm constructed sabotage fixtures",
            stderr_contains="Ran 111 tests",
        ),
        run_check(
            "egr2_integration",
            [sys.executable, "-m", "pytest", "-q", "test_egr2_integration.py"],
            egrr_dir, 0, raw_dir, stdout_contains="4 passed",
        ),
        run_check(
            "registered_fixture_benign",
            [sys.executable, str(package_dir / "registered_fixture_gate.py")],
            root, 0, raw_dir,
            stdout_contains=(
                'GATE: PASS — registered constructed payload '
                '{"correction_count":128,"payload_bytes":1311,'
            ),
        ),
        run_check(
            "registered_fixture_crc_sabotage",
            [sys.executable, str(package_dir / "registered_fixture_gate.py"),
             "--sabotage"],
            root, 1, raw_dir,
            expected_stdout="GATE: FAIL — planted CRC corruption detected\n",
        ),
        run_check(
            "reporting_benign",
            [sys.executable, "descriptive_reporting_gate.py"],
            egrr_dir, 0, raw_dir,
            expected_stdout="GATE: PASS — all positive/zero/negative cases retained\n",
        ),
        run_check(
            "reporting_sabotage",
            [sys.executable, "descriptive_reporting_gate.py", "--sabotage"],
            egrr_dir, 1, raw_dir,
            expected_stdout="GATE: FAIL — reporting completeness failure\n",
        ),
    ]
    for repeat in range(1, 4):
        checks.append(run_check(
            f"noise_repeat_{repeat}",
            [sys.executable, str(package_dir / "noise_probe.py")],
            root, 0, raw_dir,
        ))
    noise_outputs = [
        (raw_dir / f"noise_repeat_{repeat}.stdout.txt").read_bytes()
        for repeat in range(1, 4)
    ]
    noise_equal = len(set(noise_outputs)) == 1
    checks.append({
        "name": "noise_three_repeat_equality",
        "command": ["internal exact-byte comparison of noise_repeat_1..3"],
        "expected_exit": 0,
        "actual_exit": 0 if noise_equal else 1,
        "passed": noise_equal,
        "repeat_stdout_sha256": [
            hashlib.sha256(item).hexdigest() for item in noise_outputs
        ],
        "observed_variation": "none" if noise_equal else "nonzero",
    })
    summary["checks"] = checks
    summary["verification_ok"] = all(item["passed"] for item in checks)
    write_summary(summary, output_dir)
    return 0 if summary["verification_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

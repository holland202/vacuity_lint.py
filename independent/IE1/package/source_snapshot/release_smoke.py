#!/usr/bin/env python3
"""Release candidate contract checks against the *installed* CLI.

Requires a fresh virtual environment with the wheel already installed.
These checks are separate from the embedded 20-case detector self-test.
"""
import json
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import sys


def invoke(*arguments):
    return subprocess.run(
        ["vacuity-lint", *map(str, arguments)],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )


def require(condition, description):
    if not condition:
        raise AssertionError(description)
    print("PASS", description, flush=True)


def main():
    require(shutil.which("vacuity-lint") is not None, "installed executable on PATH")
    require(version("vacuity-lint") == "2.0.0", "installed metadata is v2.0.0")
    selftest = invoke("--selftest")
    require(selftest.returncode == 0 and "20/20 checks passed" in selftest.stdout,
            "20 detector self-tests via installed console command")

    with TemporaryDirectory(prefix="vacuity-release-smoke-") as tmp:
        root = Path(tmp)
        clean = root / "clean"
        bad = root / "bad"
        empty = root / "empty"
        clean.mkdir()
        bad.mkdir()
        empty.mkdir()

        (clean / "test_valid.py").write_text(
            "def test_result():\n    assert 2 + 2 == 4\n", encoding="utf-8"
        )
        (bad / "test_no_checks.py").write_text(
            "print('ran but never asserted')\n", encoding="utf-8"
        )
        (bad / "verify_prints.py").write_text(
            "import sys\nprint('[FAIL] but returns 0')\nsys.exit(0)\n",
            encoding="utf-8"
        )
        good_result = invoke(clean)
        bad_result = invoke(bad)
        empty_result = invoke(empty)
        require(good_result.returncode == 0 and "no vacuous verification found" in good_result.stdout,
                "clean source returns 0")
        require(bad_result.returncode == 1, "defective source returns 1")
        require("UNCOLLECTABLE_TEST" in bad_result.stdout, "missing-test defect reported")
        require("PRINTS_FAIL_ONLY" in bad_result.stdout or "ALWAYS_EXITS_ZERO" in bad_result.stdout,
                "prints-failure defect reported")
        require(empty_result.returncode == 2 and "nothing scanned" in empty_result.stderr,
                "empty scan returns 2, never passes as clean")

        (bad / "test_broken.py").write_text("def broken(:\n", encoding="utf-8")
        syntax_result = invoke(bad)
        require(syntax_result.returncode == 1 and "UNPARSEABLE" in syntax_result.stdout,
                "syntax errors reported as findings")

    version_result = invoke("--version")
    require(version_result.returncode == 0 and
            version_result.stdout.strip() == "vacuity-lint 2.0.0",
            "installed CLI --version matches package metadata")

    with TemporaryDirectory(prefix="vacuity-release-json-") as temp:
        root = Path(temp)
        broken = root / "verify_prints.py"
        broken.write_text('print("[FAIL] always passes")\n', encoding="utf-8")
        json_result = invoke(root, "--format", "json")
        require(json_result.returncode == 1,
                "installed JSON mode preserves findings exit code")
        data = json.loads(json_result.stdout)
        require(data["version"] == "2.0.0" and
                data["findings"][0]["rule_id"] == "VL002" and
                data["findings"][0]["category"] == "heuristic" and
                "line" not in data["findings"][0],
                "installed JSON finding has stable metadata without fake line")
        broken.unlink()
        empty_result = invoke(root, "--format", "json")
        require(empty_result.returncode == 2 and
                json.loads(empty_result.stdout)["status"] == "no_python_files",
                "installed JSON mode preserves empty-scan exit 2")

    print("RELEASE CONTRACT: PASS (v2.0.0, 13 checks)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"RELEASE CONTRACT: FAIL: {exc}", file=sys.stderr)
        sys.exit(1)

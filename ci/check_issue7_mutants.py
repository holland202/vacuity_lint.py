#!/usr/bin/env python3
"""Four focused engineering mutants; no preregistered experiment is run."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTANTS = (
    ("ignore-missing-root",
     'coverage_errors.append({"path": root, "message": str(exc)})',
     'pass  # deliberate defect: omit the requested root',
     "test_scan_integrity.ScanIntegrityTests.test_mixed_missing_root_never_clean_in_either_order_or_format"),
    ("suppress-from-string",
     'reason = _comment_suppression(src)',
     'match = SUPPRESS_RE.search(src)\n    reason = match.group(1) if match else None',
     "test_scan_integrity.ScanIntegrityTests.test_suppression_markers_inside_literals_do_not_suppress"),
    ("bare-systemexit-is-failure",
     'elif isinstance(n.exc, ast.Name) and n.exc.id == "SystemExit":\n            self.exit_calls.append("zero")',
     'elif isinstance(n.exc, ast.Name) and n.exc.id == "SystemExit":\n            self.raises += 1',
     "test_scan_integrity.ScanIntegrityTests.test_systemexit_zero_forms_cannot_supply_fail_path"),
    ("trust-shadowed-alias",
     'return {name: kind for name, kind in bindings.items() if name not in shadowed}',
     'return bindings  # deliberate defect: trust a reassigned exit alias',
     "test_exit_aliases.ExitAliasTests.test_imported_function_shadowed_by_assignment_is_not_recognized"),
)


def main():
    source = (ROOT / "vacuity_lint.py").read_text(encoding="utf-8")
    failed = []
    for name, before, after, test in MUTANTS:
        if source.count(before) != 1:
            raise AssertionError(f"{name}: mutation site is not unique")
        changed = source.replace(before, after, 1)
        compile(changed, name, "exec")
        with tempfile.TemporaryDirectory(prefix="vacuity-mutant-") as temp:
            root = Path(temp)
            (root / "vacuity_lint.py").write_text(changed, encoding="utf-8")
            for filename in ("test_scan_integrity.py", "test_exit_aliases.py"):
                shutil.copyfile(ROOT / "tests" / filename, root / filename)
            result = subprocess.run(
                [sys.executable, "-m", "unittest", test, "-v"],
                cwd=root, capture_output=True, text=True, timeout=30, check=False,
            )
        # An assertion failure kills the mutant. A crash/import error does not.
        killed = (result.returncode == 1 and "FAILED (failures=" in result.stderr
                  and "ERROR:" not in result.stderr and "errors=" not in result.stderr)
        print(name + ": " + ("KILLED" if killed else "NOT KILLED"), flush=True)
        print(result.stdout + result.stderr, end="", flush=True)
        if not killed:
            failed.append(name)
    if failed:
        raise AssertionError("mutants not killed by intended assertions: " + ", ".join(failed))
    print("ISSUE 7 MUTANTS: 4/4 killed by regression assertions")
    return 0


if __name__ == "__main__":
    sys.exit(main())


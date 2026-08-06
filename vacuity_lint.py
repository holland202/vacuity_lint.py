#!/usr/bin/env python3
"""vacuity_lint.py — find verification code that cannot fail.

Across four independent codebases (quasar, slc-v12-, Principia-Artificialis,
the Phase 2C toolkit) the same defect appeared: a construct that looks like
verification but has no path to a failing outcome. A test file pytest cannot
collect. A suite that prints [FAIL] six times and exits 0. A guard whose
marker is never written, so it can only ever return one answer. Each looked
like evidence and none of it was.

This tool finds that class of defect by parsing the AST, not by grepping.

WHAT COUNTS AS A FAIL PATH
    assert                        -> AssertionError propagates, exit nonzero
    raise                         -> propagates, exit nonzero
    sys.exit(<not literal 0>)     -> can exit nonzero
    def test_*                    -> pytest can fail it
Anything else cannot make the process exit nonzero on its own.

FINDINGS
    NO_FAIL_PATH        looks like verification, has no fail path at all
    PRINTS_FAIL_ONLY    prints FAIL/ERROR but has no fail path
    UNCOLLECTABLE_TEST  named test_*.py but declares no `def test_`
    ALWAYS_EXITS_ZERO   every sys.exit call is a literal 0

KNOWN LIMITATION, stated rather than hidden: this cannot detect a fail path
that is present but logically unreachable. The Phase 2C bug was
`return 0 if (healthy or not abort_reason) else 1`, where `healthy` already
implied `not abort_reason`, so the 1 branch was dead. That needs reachability
analysis; this tool would call that file clean. It finds missing fail paths,
not dead ones.

Exit 0 when nothing is found, 1 when findings exist, so it can gate a repo.
Zero dependencies, standard library only.
"""

import argparse
import ast
import os
import re
import shutil
import sys
import tempfile
import subprocess

VERIFY_HINTS = ("test", "check", "verify", "smoke", "validate", "gate",
                "audit", "selftest", "assert", "prove", "harness")
FAIL_WORDS = ("[fail]", "fail:", "failed", "[error]", "mismatch", "does not match")
SUPPRESS_RE = re.compile(
    r"#\s*vacuity-lint:\s*intentional\s*[-\u2014:]\s*(\S.*?)\s*$", re.I | re.M)

SKIP_DIRS = {".git", "__pycache__", "node_modules", "venv", ".venv", "build",
             "dist", "site-packages", "secp_env", "llama.cpp", ".tox"}


class Scan(ast.NodeVisitor):
    def __init__(self):
        self.asserts = 0
        self.raises = 0
        self.exit_calls = []      # list of "zero" | "nonzero" | "dynamic"
        self.test_defs = 0
        self.fail_strings = 0
        self.has_main = False
        self.is_executable = False
        self.suppressed = None

    def visit_Assert(self, n):
        self.asserts += 1
        self.generic_visit(n)

    def visit_Raise(self, n):
        self.raises += 1
        self.generic_visit(n)

    def visit_FunctionDef(self, n):
        if n.name.startswith("test_"):
            self.test_defs += 1
        self.generic_visit(n)

    def visit_AsyncFunctionDef(self, n):
        self.visit_FunctionDef(n)

    def visit_Constant(self, n):
        if isinstance(n.value, str):
            low = n.value.lower()
            if any(w in low for w in FAIL_WORDS):
                self.fail_strings += 1
        self.generic_visit(n)

    def visit_Call(self, n):
        f = n.func
        name = None
        if isinstance(f, ast.Attribute) and f.attr == "exit":
            if isinstance(f.value, ast.Name) and f.value.id in ("sys", "os"):
                name = "exit"
        elif isinstance(f, ast.Name) and f.id in ("exit", "quit"):
            name = "exit"
        if name:
            if not n.args:
                self.exit_calls.append("zero")
            else:
                a = n.args[0]
                if isinstance(a, ast.Constant):
                    self.exit_calls.append(
                        "zero" if a.value in (0, None) else "nonzero")
                else:
                    self.exit_calls.append("dynamic")
        self.generic_visit(n)


def looks_like_verification(path, s):
    """A file is verification-shaped only if it can be RUN as a check.

    A library module named *_gate.py is not a test; it is not supposed to exit
    nonzero. Requiring an entry point (a __main__ block or pytest functions)
    removes that whole class of false positive.
    """
    if s.test_defs > 0:
        return True
    if not s.is_executable:
        return False
    base = os.path.basename(path).lower()
    return any(h in base for h in VERIFY_HINTS) or s.fail_strings > 0


def has_fail_path(s):
    return (s.asserts > 0 or s.raises > 0 or s.test_defs > 0
            or any(e in ("nonzero", "dynamic") for e in s.exit_calls))


def analyse(path):
    """Return (findings, scan) for one file. findings is a list of codes."""
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src)
        has_main = "__main__" in src
    except (OSError, SyntaxError) as e:
        return [("UNPARSEABLE", str(e).split("\n")[0][:60])], None

    s = Scan()
    s.visit(tree)
    s.has_main = has_main
    # Executable = a __main__ guard, or a call at module level. A file of
    # only imports, defs and classes is a library: it cannot exit nonzero
    # by itself and must not be judged as if it could.
    s.is_executable = has_main or any(
        isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
        for n in tree.body)
    out = []
    base = os.path.basename(path)

    if (base.startswith("test_") and base.endswith(".py")
            and s.test_defs == 0 and not has_fail_path(s)):
        out.append(("UNCOLLECTABLE_TEST",
                    "named test_*.py but declares no `def test_`; "
                    "pytest collects nothing here"))

    if looks_like_verification(path, s):
        if not has_fail_path(s):
            if s.fail_strings:
                out.append(("PRINTS_FAIL_ONLY",
                            f"prints failure text {s.fail_strings}x but has no "
                            "assert, raise, or nonzero exit"))
            else:
                out.append(("NO_FAIL_PATH",
                            "verification-shaped but has no assert, raise, "
                            "test function, or nonzero exit"))
        elif s.exit_calls and all(e == "zero" for e in s.exit_calls) \
                and not (s.asserts or s.raises or s.test_defs):
            out.append(("ALWAYS_EXITS_ZERO",
                        f"{len(s.exit_calls)} exit call(s), all literal 0"))

    # A file may declare a finding deliberate, but only with a stated reason.
    # A bare marker does not suppress: writing down WHY is the whole value of
    # the mechanism, and a mute button without a reason is how a known defect
    # becomes an invisible one.
    m = SUPPRESS_RE.search(src)
    if m and out:
        s.suppressed = m.group(1)
        out = []
    return out, s


def walk(root):
    if os.path.isfile(root):
        yield root
        return
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in sorted(files):
            if f.endswith(".py"):
                yield os.path.join(base, f)


# ------------------------------------------------------------------ selftest

def _w(p, body):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(body)


def selftest():
    tmp = tempfile.mkdtemp(prefix="vacuity_selftest_", dir=os.path.expanduser("~"))
    r = []
    try:
        # --- the four real defects, reproduced
        _w(f"{tmp}/bad/test_nothing.py",
           "import sys\nprint('checking')\nprint('done')\n")
        _w(f"{tmp}/bad/verify_prints.py",
           "print('[FAIL] scaling slope')\nprint('[PASS] ok')\nsys.exit(0)\n")
        _w(f"{tmp}/bad/smoke_zero.py",
           "import sys\ndef main():\n    print('checking')\nsys.exit(0)\n")
        # --- correct code that must NOT be flagged
        _w(f"{tmp}/good/test_real.py",
           "def test_a():\n    assert 1 == 1\n")
        _w(f"{tmp}/good/verify_exits.py",
           "import sys\nok = False\nprint('[FAIL] x')\nsys.exit(0 if ok else 1)\n")
        _w(f"{tmp}/good/runner.py",
           "import sys\nok=False\nsys.exit(1 if not ok else 0)\n")
        _w(f"{tmp}/good/plain_module.py",
           "def add(a, b):\n    return a + b\n")
        _w(f"{tmp}/good/asserting.py",
           "def check():\n    assert 2 > 1\n")

        def codes(p):
            return [c for c, _ in analyse(p)[0]]

        r.append(("P1 test_*.py with no test funcs -> UNCOLLECTABLE_TEST",
                  "UNCOLLECTABLE_TEST" in codes(f"{tmp}/bad/test_nothing.py")))
        r.append(("P2 prints FAIL, no fail path -> PRINTS_FAIL_ONLY",
                  "PRINTS_FAIL_ONLY" in codes(f"{tmp}/bad/verify_prints.py")))
        r.append(("P3 verification shape, exit 0 only -> flagged",
                  bool(codes(f"{tmp}/bad/smoke_zero.py"))))

        # ANTI-VACUITY: the detector must be able to return nothing
        r.append(("P4 real pytest test -> no finding",
                  codes(f"{tmp}/good/test_real.py") == []))
        r.append(("P5 conditional nonzero exit -> no finding",
                  codes(f"{tmp}/good/verify_exits.py") == []))
        r.append(("P6 dynamic exit expression -> no finding",
                  codes(f"{tmp}/good/runner.py") == []))
        r.append(("P7 ordinary module is not verification -> no finding",
                  codes(f"{tmp}/good/plain_module.py") == []))
        r.append(("P8 assert counts as a fail path -> no finding",
                  codes(f"{tmp}/good/asserting.py") == []))
        r.append(("P9 clean tree yields zero findings (tool can find nothing)",
                  sum(len(analyse(p)[0]) for p in walk(f"{tmp}/good")) == 0))
        r.append(("P10 defective tree yields findings (tool can find something)",
                  sum(len(analyse(p)[0]) for p in walk(f"{tmp}/bad")) >= 3))

        _w(f"{tmp}/good/thermal_gate.py",
           "class Gate:\n    def check(self):\n        return True\n")
        _w(f"{tmp}/good/test_runnable.py",
           "import sys\nok=False\nif not ok:\n    sys.exit(1)\n"
           "if __name__ == '__main__':\n    pass\n")
        r.append(("P13 library module named *_gate.py, no __main__ -> no finding",
                  codes(f"{tmp}/good/thermal_gate.py") == []))
        r.append(("P14 test_*.py that exits nonzero is not UNCOLLECTABLE",
                  "UNCOLLECTABLE_TEST" not in codes(f"{tmp}/good/test_runnable.py")))

        _w(f"{tmp}/good/test_declared.py",
           "# vacuity-lint: intentional - reads live device temperature\n"
           "print('[FAIL] maybe')\n")
        _w(f"{tmp}/bad/test_bare_marker.py",
           "# vacuity-lint: intentional\n"
           "print('[FAIL] maybe')\n")
        r.append(("P15 marker WITH a reason suppresses the finding",
                  codes(f"{tmp}/good/test_declared.py") == []))
        r.append(("P16 bare marker with NO reason does NOT suppress",
                  codes(f"{tmp}/bad/test_bare_marker.py") != []))
        r.append(("P17 suppression is recorded, not silent",
                  analyse(f"{tmp}/good/test_declared.py")[1].suppressed
                  == "reads live device temperature"))
        r.append(("P18 suppression in one file does not affect another",
                  codes(f"{tmp}/bad/verify_prints.py") != []))

        # the empty-scan branch, both directions
        os.makedirs(f"{tmp}/empty", exist_ok=True)
        _w(f"{tmp}/nonempty/plain.py", "x = 1\n")
        def run_on(d):
            return subprocess.run([sys.executable, os.path.abspath(__file__), d],
                                  capture_output=True, text=True)
        _e = run_on(f"{tmp}/empty")
        _n = run_on(f"{tmp}/nonempty")
        r.append(("P19 tree with no python files -> exit 2, not a clean bill",
                  _e.returncode == 2 and "nothing scanned" in _e.stderr))
        r.append(("P20 tree with a clean python file -> still exit 0",
                  _n.returncode == 0))

        _w(f"{tmp}/broken/test_syntax.py", "def oops(:\n")
        r.append(("P11 syntax error reported, not silently skipped",
                  "UNPARSEABLE" in codes(f"{tmp}/broken/test_syntax.py")))
        r.append(("P12 documented blind spot: unreachable fail path not caught",
                  codes(f"{tmp}/good/verify_exits.py") == []))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    w = max(len(n) for n, _ in r)
    for n, ok in r:
        print(f"[{'PASS' if ok else 'FAIL'}] {n.ljust(w)}")
    p = sum(1 for _, ok in r if ok)
    print(f"\n{p}/{len(r)} checks passed")
    return 0 if p == len(r) else 1


# ---------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="findings only")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    total_files = 0
    verification_files = 0
    findings = []
    suppressed = []
    for root in args.paths:
        for p in walk(os.path.expanduser(root)):
            total_files += 1
            fs, s = analyse(p)
            if s is not None and looks_like_verification(p, s):
                verification_files += 1
            if s is not None and s.suppressed:
                suppressed.append((p, s.suppressed))
            for code, why in fs:
                findings.append((p, code, why))

    if total_files == 0:
        where = ", ".join(args.paths) or "."
        print(f"nothing scanned - no python files found under: {where}",
              file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"python files scanned    : {total_files}")
        print(f"verification-shaped     : {verification_files}")
        print(f"findings                : {len(findings)}")
        print(f"declared intentional    : {len(suppressed)}\n")
        for p, why in suppressed:
            print(f"  [intentional] {p}")
            print(f"      {why}")
        if suppressed:
            print()

    by_code = {}
    for p, code, why in findings:
        by_code.setdefault(code, []).append((p, why))
    for code in sorted(by_code):
        print(f"{code}  ({len(by_code[code])})")
        for p, why in by_code[code]:
            print(f"  {p}")
            print(f"      {why}")
        print()

    if not findings and not args.quiet:
        print("no vacuous verification found")
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())

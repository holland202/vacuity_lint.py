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
    ordinary raise                -> potential nonzero failure
    nonzero/dynamic exit code     -> potential nonzero failure
    os.abort()                    -> nonzero termination
    pytest.fail()                 -> raises pytest's Failed (real pytest only)
    def test_*                    -> pytest can fail it
Simple stdlib exit aliases are recognized unless shadowed. This is a
syntactic inventory, not a proof about reachable outcomes.

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

Exit 0 for a complete nonempty scan without findings; 1 for findings,
including syntax-error VL005; 2 for empty scans or filesystem coverage errors.
Zero dependencies, standard library only.
"""

import argparse
import ast
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import tokenize
import subprocess

__version__ = "2.0.1.dev0"

# Public rule identifiers are stable across JSON consumers.
# Category separates incomplete analysis from heuristic review prompts.
RULE_INFO = {
    "NO_FAIL_PATH": ("VL001", "warning", "heuristic"),
    "PRINTS_FAIL_ONLY": ("VL002", "warning", "heuristic"),
    "UNCOLLECTABLE_TEST": ("VL003", "warning", "heuristic"),
    "ALWAYS_EXITS_ZERO": ("VL004", "warning", "heuristic"),
    "UNPARSEABLE": ("VL005", "error", "analysis_error"),
}

VERIFY_HINTS = ("test", "check", "verify", "smoke", "validate", "gate",
                "audit", "selftest", "assert", "prove", "harness")
FAIL_WORDS = ("[fail]", "fail:", "failed", "[error]", "mismatch", "does not match")
SUPPRESS_RE = re.compile(
    r"#\s*vacuity-lint:\s*intentional\s*[-\u2014:]\s*(\S.*?)\s*$", re.I | re.M)

SKIP_DIRS = {".git", "__pycache__", "node_modules", "venv", ".venv", "build",
             "dist", "site-packages", "secp_env", "llama.cpp", ".tox"}


def _exit_code_kind(argument):
    """Classify the AST of an exit code without evaluating source code."""
    if isinstance(argument, ast.Constant):
        value = argument.value
        return "zero" if value is None or (isinstance(value, int) and value == 0) else "nonzero"
    return "dynamic"


def _exit_bindings(tree):
    """Recognize simple stdlib imports, conservatively rejecting shadowed names.

    This is not Python name-resolution or control-flow analysis. A binding
    anywhere in the file disables that alias, including in nested scopes.
    """
    bindings = {"sys": ("module", "sys"), "os": ("module", "os"),
                "exit": ("call", "exit"), "quit": ("call", "exit")}
    trusted = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                # VL-FP-002: `pytest` is tracked only so `pytest.fail(...)` can count as a fail path.
                if alias.name in ("sys", "os", "pytest"):
                    name = alias.asname or alias.name
                    bindings[name] = ("module", alias.name)
                    trusted.add((id(node), name))
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            for alias in node.names:
                kind = ("exit" if node.module == "sys" and alias.name == "exit"
                        else alias.name if node.module == "os" and alias.name in ("_exit", "abort")
                        else "pytest_fail" if node.module == "pytest" and alias.name == "fail"
                        else None)
                if kind is not None:
                    name = alias.asname or alias.name
                    bindings[name] = ("call", kind)
                    trusted.add((id(node), name))
    shadowed = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            shadowed.add(node.id)
        elif isinstance(node, ast.arg):
            shadowed.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            shadowed.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            shadowed.add(node.name)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            shadowed.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            shadowed.add(node.rest)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    shadowed.update(bindings)
                name = alias.asname or alias.name.split(".")[0]
                if (id(node), name) not in trusted:
                    shadowed.add(name)
    return {name: kind for name, kind in bindings.items() if name not in shadowed}


def _is_main_guard(stmt):
    """Accept only real top-level __name__ == '__main__' guards."""
    if not isinstance(stmt, ast.If):
        return False
    check = stmt.test
    if not (isinstance(check, ast.Compare) and len(check.ops) == 1
            and isinstance(check.ops[0], ast.Eq) and len(check.comparators) == 1):
        return False
    left, right = check.left, check.comparators[0]
    return (
        isinstance(left, ast.Name) and left.id == "__name__"
        and isinstance(right, ast.Constant) and right.value == "__main__"
    ) or (
        isinstance(right, ast.Name) and right.id == "__name__"
        and isinstance(left, ast.Constant) and left.value == "__main__"
    )


def _runs_a_check(stmt):
    """VL-FP-001 (post hoc, see VLFP001/RESULTS.md): a top-level try/if/for/while/with block whose own
    statements (not nested defs or classes) contain an assert or a bare call statement runs at import or
    execution time. Blocks of only imports and assignments (e.g. optional-import fallbacks) do not count."""
    if not isinstance(stmt, (ast.Try, ast.If, ast.For, ast.While, ast.With)) and type(stmt).__name__ != "TryStar":
        return False
    stack = list(ast.iter_child_nodes(stmt))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(node, ast.Assert) or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
            return True
        stack.extend(ast.iter_child_nodes(node))
    return False


class Scan(ast.NodeVisitor):
    def __init__(self, tree=None):
        self.exit_bindings = _exit_bindings(
            tree if tree is not None else ast.Module(body=[], type_ignores=[]))
        self.asserts = 0
        self.raises = 0
        self.exit_calls = []      # list of "zero" | "nonzero" | "dynamic"
        self.test_defs = 0
        self.test_names = set()
        self.names_used = set()
        self.runner_imported = False
        self.tautological_asserts = 0   # VL-FP-001: assert (x, "msg") / assert True cannot fail
        self.swallowed_asserts = 0      # VL-FP-001: assert inside try whose AssertionError is swallowed
        self._swallow_depth = 0
        self.fail_strings = 0
        self._data_depth = 0            # VL-FP-003: >0 while inside a tuple/list/set/dict literal
        self.has_main = False
        self.is_executable = False
        self.suppressed = None

    def visit_Assert(self, n):
        t = n.test
        # `assert (x, "msg")`: a non-empty tuple is always true (Python itself warns). A bare
        # `assert True` is deliberately NOT reclassified: the frozen IE1 independent cases record it as
        # clean / a documented blind spot (VLFP001/RESULTS.md, V-B withdrawn).
        if isinstance(t, ast.Tuple) and t.elts:
            self.tautological_asserts += 1
        elif self._swallow_depth:
            self.swallowed_asserts += 1
        else:
            self.asserts += 1
        self.generic_visit(n)

    @staticmethod
    def _handler_swallows(h):
        """A handler that can catch AssertionError and neither re-raises nor exits."""
        caught = h.type
        names = []
        if caught is None:
            names = ["BaseException"]
        else:
            for e in (caught.elts if isinstance(caught, ast.Tuple) else [caught]):
                if isinstance(e, ast.Name):
                    names.append(e.id)
                elif isinstance(e, ast.Attribute):
                    names.append(e.attr)
        if not set(names) & {"AssertionError", "Exception", "BaseException"}:
            return False
        for node in ast.walk(ast.Module(body=h.body, type_ignores=[])):
            if isinstance(node, ast.Raise):
                return False
            if isinstance(node, ast.Call):
                f = node.func
                attr = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
                if attr in ("exit", "_exit", "abort", "fail"):
                    return False   # conservative: any exit-like call keeps the assert counted
        return True

    def visit_Try(self, n):
        swallows = any(self._handler_swallows(h) for h in n.handlers)
        if swallows:
            self._swallow_depth += 1
        for stmt in n.body:
            self.visit(stmt)
        if swallows:
            self._swallow_depth -= 1
        for part in (n.handlers, n.orelse, n.finalbody):
            for stmt in part:
                self.visit(stmt)

    visit_TryStar = visit_Try

    def visit_Lambda(self, n):
        depth, self._swallow_depth = self._swallow_depth, 0
        self.generic_visit(n)
        self._swallow_depth = depth

    def visit_ClassDef(self, n):
        depth, self._swallow_depth = self._swallow_depth, 0
        self.generic_visit(n)
        self._swallow_depth = depth

    def visit_Import(self, n):
        if any(a.name.split(".")[0] in ("unittest", "pytest") for a in n.names):
            self.runner_imported = True
        self.generic_visit(n)

    def visit_ImportFrom(self, n):
        if (n.module or "").split(".")[0] in ("unittest", "pytest"):
            self.runner_imported = True
        self.generic_visit(n)

    def visit_Name(self, n):
        if isinstance(n.ctx, ast.Load):
            self.names_used.add(n.id)
        self.generic_visit(n)

    def visit_Attribute(self, n):
        self.names_used.add(n.attr)
        self.generic_visit(n)

    def visit_Raise(self, n):
        # SystemExit(0) is a successful exit, not a fail path.
        # Keep other raises counted as potential failures.
        if (isinstance(n.exc, ast.Call)
                and isinstance(n.exc.func, ast.Name)
                and n.exc.func.id == "SystemExit"):
            self.exit_calls.append(
                "nonzero" if len(n.exc.args) > 1 else
                _exit_code_kind(n.exc.args[0]) if n.exc.args else "zero")
        elif isinstance(n.exc, ast.Name) and n.exc.id == "SystemExit":
            self.exit_calls.append("zero")
        else:
            self.raises += 1
        self.generic_visit(n)

    def visit_FunctionDef(self, n):
        if n.name.startswith("test_"):
            self.test_defs += 1
            self.test_names.add(n.name)
        depth, self._swallow_depth = self._swallow_depth, 0   # a def's body does not run inside the try
        self.generic_visit(n)
        self._swallow_depth = depth

    def visit_AsyncFunctionDef(self, n):
        self.visit_FunctionDef(n)

    def visit_Constant(self, n):
        if isinstance(n.value, str) and not self._data_depth:
            low = n.value.lower()
            if any(w in low for w in FAIL_WORDS):
                self.fail_strings += 1
        self.generic_visit(n)

    def _visit_data_literal(self, n):
        """VL-FP-003: a string inside a tuple/list/set/dict literal is data (a status-code table, an enum
        member's phrase), not a printed failure message. Known blind spot, recorded in VLFP003/RESULTS.md:
        a failure message stored in a list and printed later is no longer counted."""
        self._data_depth += 1
        self.generic_visit(n)
        self._data_depth -= 1

    visit_Tuple = visit_List = visit_Set = visit_Dict = _visit_data_literal

    def _is_pytest_fail(self, call):
        """VL-FP-002: `pytest.fail(...)` raises pytest's Failed, so it is a fail path like `raise`.

        Counted only through a trusted, unshadowed top-level `import pytest [as x]` or
        `from pytest import fail [as y]` (the same binding rule as sys/os exits).
        """
        f = call.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            return f.attr == "fail" and self.exit_bindings.get(f.value.id) == ("module", "pytest")
        if isinstance(f, ast.Name):
            return self.exit_bindings.get(f.id) == ("call", "pytest_fail")
        return False

    def visit_Call(self, n):
        if self._is_pytest_fail(n):
            self.raises += 1
            self.generic_visit(n)
            return
        f = n.func
        name = None
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            module = self.exit_bindings.get(f.value.id)
            if module == ("module", "sys") and f.attr == "exit":
                name = "exit"
            elif module == ("module", "os") and f.attr in ("_exit", "abort"):
                name = f.attr
        elif isinstance(f, ast.Name):
            binding = self.exit_bindings.get(f.id)
            if binding is not None and binding[0] == "call" and binding[1] != "pytest_fail":
                name = binding[1]
        if name:
            self.exit_calls.append(
                "nonzero" if name == "abort" or len(n.args) > 1 else
                _exit_code_kind(n.args[0]) if n.args else "zero")
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


def effective_test_defs(s, path=None):
    """VL-FP-001: `def test_*` counts as a fail path only if something can run it: pytest's default
    collection (test_*.py / *_test.py), an imported unittest/pytest runner, or a call in the module."""
    if not s.test_defs:
        return 0
    base = os.path.basename(path or getattr(s, "path", "") or "")
    if base.startswith("test_") or base.endswith("_test.py") or s.runner_imported:
        return s.test_defs
    return len(s.test_names & s.names_used)


def has_fail_path(s):
    return (s.asserts > 0 or s.raises > 0 or effective_test_defs(s) > 0
            or any(e in ("nonzero", "dynamic") for e in s.exit_calls))


def _comment_suppression(src):
    """A quoted example is source data, not a suppression declaration."""
    try:
        for token in tokenize.generate_tokens(io.StringIO(src).readline):
            if token.type == tokenize.COMMENT:
                match = SUPPRESS_RE.search(token.string)
                if match:
                    return match.group(1)
    except (tokenize.TokenError, IndentationError):
        # If comment identity cannot be established, never suppress a finding.
        pass
    return None


def analyse(path, *, strict_io=False):
    """Return (findings, scan) for one file. findings is a list of codes."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        tree = ast.parse(src)
        has_main = any(_is_main_guard(n) for n in tree.body)
    except OSError as e:
        if strict_io:
            raise
        return [("UNPARSEABLE", str(e).split("\n")[0][:60])], None
    except SyntaxError as e:
        return [("UNPARSEABLE", str(e).split("\n")[0][:60])], None

    s = Scan(tree)
    s.path = path
    s.visit(tree)
    s.has_main = has_main
    # Executable = a __main__ guard, or a call at module level. A file of
    # only imports, defs and classes is a library: it cannot exit nonzero
    # by itself and must not be judged as if it could.
    s.is_executable = has_main or any(
        isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
        for n in tree.body) or any(_runs_a_check(n) for n in tree.body)
    out = []
    base = os.path.basename(path)

    if (base.startswith("test_") and base.endswith(".py")
            and s.test_defs == 0 and not has_fail_path(s)):
        out.append(("UNCOLLECTABLE_TEST",
                    "named test_*.py but declares no `def test_`; "
                    "pytest collects nothing here"))

    if looks_like_verification(path, s):
        # Prefer a printed-failure finding when a zero-only checker
        # announces errors; otherwise use the more precise exit category.
        if (s.exit_calls and all(e == "zero" for e in s.exit_calls)
                and not (s.asserts or s.raises or effective_test_defs(s) or s.fail_strings)):
            out.append(("ALWAYS_EXITS_ZERO",
                        f"{len(s.exit_calls)} exit call(s), all literal 0"))
        elif not has_fail_path(s):
            if s.fail_strings:
                out.append(("PRINTS_FAIL_ONLY",
                            f"contains failure text {s.fail_strings}x but has no "
                            "assert, raise, or nonzero exit"))
            else:
                out.append(("NO_FAIL_PATH",
                            "verification-shaped but has no assert, raise, "
                            "test function, or nonzero exit"))
 
    # A file may declare a finding deliberate, but only with a stated reason.
    # A bare marker does not suppress: writing down WHY is the whole value of
    # the mechanism, and a mute button without a reason is how a known defect
    # becomes an invisible one.
    reason = _comment_suppression(src)
    if reason and out:
        s.suppressed = reason
        out = []
    return out, s


def walk(root):
    mode = os.stat(root).st_mode
    if stat.S_ISREG(mode):
        yield root
        return
    if not stat.S_ISDIR(mode):
        raise OSError(f"scan path is not a regular file or directory: {root}")

    def traversal_error(error):
        raise error

    for base, dirs, files in os.walk(root, onerror=traversal_error):
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
    ap.add_argument("--quiet", action="store_true", help="findings only in text mode")
    ap.add_argument("--format", choices=("text", "json"), default="text",
                    help="output format; JSON uses stable rule IDs and no unverified line numbers")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    total_files = 0
    verification_files = 0
    findings = []
    suppressed = []
    coverage_errors = []
    for root in args.paths:
        try:
            for p in walk(os.path.expanduser(root)):
                total_files += 1
                try:
                    fs, s = analyse(p, strict_io=True)
                except OSError as exc:
                    coverage_errors.append({"path": p, "message": str(exc)})
                    continue
                if s is not None and looks_like_verification(p, s):
                    verification_files += 1
                if s is not None and s.suppressed:
                    suppressed.append((p, s.suppressed))
                for code, why in fs:
                    findings.append((p, code, why))
        except OSError as exc:
            coverage_errors.append({"path": root, "message": str(exc)})

    if args.format == "json":
        data = {
            "tool": "vacuity-lint",
            "version": __version__,
            "files_scanned": total_files,
            "verification_shaped": verification_files,
            "status": (
                "analysis_error" if coverage_errors else
                "no_python_files" if total_files == 0 else
                "findings" if findings else "clean"
            ),
            "findings": [
                {
                    "rule_id": RULE_INFO[code][0],
                    "rule": code,
                    "severity": RULE_INFO[code][1],
                    "category": RULE_INFO[code][2],
                    "path": path,
                    "message": message,
                    "suppressed": False,
                }
                for path, code, message in sorted(findings)
            ],
            "suppressions": [
                {"path": path, "reason": reason, "suppressed": True}
                for path, reason in sorted(suppressed)
            ],
            "coverage_errors": coverage_errors,
        }
        # Per-file classification does not establish a truthful line number.
        # Never invent one for machine-readable diagnostics.
        print(json.dumps(data, indent=2, sort_keys=True))
        return 2 if coverage_errors or total_files == 0 else 1 if findings else 0

    for error in coverage_errors:
        print(f"could not scan {error['path']}: {error['message']}", file=sys.stderr)

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

    if not findings and not coverage_errors and not args.quiet:
        print("no vacuous verification found")
    return 2 if coverage_errors else 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

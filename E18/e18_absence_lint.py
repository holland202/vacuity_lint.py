"""AL001 — absence-only tests: every assertion satisfiable by the empty world.

Standalone AST scanner registered in E18/PREREG.md. vacuity_lint.py is not
imported and not modified. Scope: functions named test_* in files named
test*.py. A finding is a scoped function with >= 1 recognized assertion, all
of them empty-satisfiable per the registered table. Zero-assertion functions
are out of scope. Exit: 1 findings, 0 clean, 2 could not look (zero test
files scanned is exit 2, never a clean verdict).
"""
import ast
import json
import sys
from pathlib import Path

NEGATIVE_METHODS = {
    "assertNotIn", "assertNotEqual", "assertNotEquals", "assertFalse",
    "assertNotRegex", "assertNotIsInstance", "assertIsNone",
    "assertNotAlmostEqual", "assert_not_called",
}
EQUALITY_METHODS = {"assertEqual", "assertEquals"}
TRUTH_METHODS = {"assertTrue"}
# Registered sabotage (P2): these three become POSITIVE under --sabotage.
SABOTAGED = {"assertNotIn", "assertNotEqual", "assertFalse"}


def is_empty_literal(node):
    if isinstance(node, ast.Constant):
        return node.value in (0, "", b"", None, False) and node.value is not True
    if isinstance(node, (ast.List, ast.Tuple)) and not node.elts:
        return True
    if isinstance(node, ast.Dict) and not node.keys:
        return True
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "set" and not node.args and not node.keywords):
        return True
    return False


def expr_is_negative(x):
    """The registered expression forms: not …, not in, !=, is None, len()==0, == empty."""
    if isinstance(x, ast.UnaryOp) and isinstance(x.op, ast.Not):
        return True
    if isinstance(x, ast.Compare) and len(x.ops) == 1:
        op, right = x.ops[0], x.comparators[0]
        if isinstance(op, ast.NotIn):
            return True
        if isinstance(op, ast.NotEq):
            return True
        if isinstance(op, ast.Is) and isinstance(right, ast.Constant) and right.value is None:
            return True
        if isinstance(op, ast.Eq):
            left = x.left
            if (isinstance(left, ast.Call) and isinstance(left.func, ast.Name)
                    and left.func.id == "len" and is_empty_literal(right) and getattr(right, "value", 1) == 0):
                return True
            if is_empty_literal(right) or is_empty_literal(left):
                return True
    return False


def classify(node, sabotage=False):
    """Return 'neg', 'pos', or None (not a recognized assertion)."""
    if isinstance(node, ast.Assert):
        return "neg" if expr_is_negative(node.test) else "pos"
    if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
        return None
    call = node.value
    if not isinstance(call.func, ast.Attribute):
        return None
    name = call.func.attr
    if name in NEGATIVE_METHODS:
        if sabotage and name in SABOTAGED:
            return "pos"
        return "neg"
    if name in EQUALITY_METHODS:
        args = call.args
        if len(args) >= 2 and (is_empty_literal(args[0]) or is_empty_literal(args[1])):
            return "neg"
        return "pos"
    if name in TRUTH_METHODS:
        return "neg" if (call.args and expr_is_negative(call.args[0])) else "pos"
    if name.startswith("assert"):
        return "pos"
    return None


def scan_file(path, sabotage=False):
    findings = []
    try:
        tree = ast.parse(Path(path).read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        return [{"file": str(path), "error": f"could not parse: {exc.msg}", "line": exc.lineno}]
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        kinds = [k for k in (classify(ch, sabotage) for ch in ast.walk(node)) if k]
        for ch in ast.walk(node):
            if isinstance(ch, (ast.With, ast.AsyncWith)):
                for item in ch.items:
                    c = item.context_expr
                    if (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                            and c.func.attr.startswith("assert")):
                        kinds.append("pos")
        if kinds and all(k == "neg" for k in kinds):
            findings.append({"file": str(path), "line": node.lineno, "function": node.name,
                            "rule": "AL001", "assertions": len(kinds)})
    return findings


def scan_tree(root, sabotage=False):
    root = Path(root)
    files = sorted(p for p in root.rglob("test*.py")
                   if ".git" not in p.parts and "E18" not in p.parts)
    findings = []
    for f in files:
        findings.extend(scan_file(f, sabotage))
    return files, findings


def main(argv):
    sabotage = "--sabotage" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        print("usage: e18_absence_lint.py [--sabotage] PATH [PATH...]")
        return 2
    total_files, all_findings = 0, []
    for p in paths:
        files, findings = scan_tree(p, sabotage)
        total_files += len(files)
        all_findings.extend(findings)
    if total_files == 0:
        print("AL001: zero test files found under the given paths; refusing a clean verdict")
        return 2
    print(json.dumps({"scanned_test_files": total_files, "sabotage": sabotage,
                      "findings": all_findings}, indent=1))
    return 1 if all_findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

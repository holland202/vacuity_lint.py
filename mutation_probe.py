#!/usr/bin/env python3
"""
mutation_probe.py -- does this check's verdict actually depend on its own logic?

vacuity_lint.py asks "is there a reachable nonzero exit at all" (Type A/B, per
note057). That is necessary but not sufficient: a script can have a perfectly
reachable sys.exit(1) whose condition never actually depends on the thing it
claims to check. This tool asks the next question -- mutation testing, in the
sense of Kupferman/Li/Seshia (FMCAD 2008) and, earlier, Beer/Ben-David/Eisner/
Rodeh's ACTL vacuity work: take the checked artifact, apply a small syntactic
mutation to it, and ask whether the verdict changes. If it doesn't, the check
never depended on that piece of logic -- a MUTATION SURVIVED. If it does, the
mutation was KILLED, and that is evidence (not proof) the check is load-bearing
there.

This is the offline analogue of what note057's LOUD/QUIET/GATED fixtures did
by hand, and of the --sabotage flags added to igar's two tests and to
vacuity_lint's own gate.yml on 2026-08-14. Formalized here so it applies to any
script, not one hand-built fixture per finding.

Mutation operators (deliberately small and well-understood; the "boundary" and
"negation" operators used by mutmut/PIT and by the literature above):
  - comparison boundary: < <-> <=,  > <-> >=,  == <-> !=
  - boolean constant flip: True <-> False
  - boolean connective swap: and <-> or

Verdict per mutation:
  KILLED    exit code changed from baseline -> the mutated line mattered here
  SURVIVED  exit code unchanged             -> the check did not depend on it
  ERROR     mutant did not even run (unparse/syntax failure unrelated to logic)

Mutation score = killed / (killed + survived). A well-gated verdict line can
still score under 100% if surrounding code has dead comparisons; a low score
localizes exactly which lines are decorative.

IMPLEMENTATION NOTE, because it was the first bug this tool found in itself:
mutating via deepcopy-and-match-by-id(...) is wrong -- deepcopy allocates new
objects with new ids, so an id captured before the copy never matches anything
in it, every mutation silently applies to nothing, and every verdict comes
back SURVIVED regardless of input. That is a Type-A-shaped bug in exactly the
tool meant to catch Type-A-shaped bugs. Fixed here by never deep-copying:
each mutant is produced by re-parsing the ORIGINAL SOURCE TEXT fresh and
walking it to the Nth eligible node (ast.walk order is deterministic for
identical source), so the mutation always lands on a live node in a live tree.

ANTI-VACUITY, mandatory: --selftest builds two fixtures, one where the guard
genuinely depends on its comparison (must show >=1 KILLED) and one where it
does not (must show >=1 SURVIVED). If either fails, this tool is reporting
findings it cannot back and must not be trusted or used until fixed.

Usage:
  python3 mutation_probe.py --selftest
  python3 mutation_probe.py TARGET.py [--timeout 30]
"""
import argparse
import ast
import os
import subprocess
import sys
import tempfile

BOUNDARY = {
    ast.Lt: ast.LtE, ast.LtE: ast.Lt,
    ast.Gt: ast.GtE, ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
}
BOOLOP = {ast.And: ast.Or, ast.Or: ast.And}


def eligible_nodes(tree):
    """Deterministic ordered list of (kind, node) for every mutable node,
    walking in ast.walk's fixed order. Re-parsing identical source and
    calling this again yields nodes in the same order every time -- that is
    what lets index i always refer to 'the same site' across a fresh parse."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in BOUNDARY:
            out.append(("compare", node))
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            out.append(("boolconst", node))
        elif isinstance(node, ast.BoolOp) and type(node.op) in BOOLOP:
            out.append(("boolop", node))
    return out


def describe(kind, node):
    if kind == "compare":
        op = type(node.ops[0]).__name__
        return node.lineno, node.col_offset, f"{op} -> {BOUNDARY[type(node.ops[0])].__name__}"
    if kind == "boolconst":
        return node.lineno, node.col_offset, f"{node.value} -> {not node.value}"
    if kind == "boolop":
        op = type(node.op).__name__
        return node.lineno, node.col_offset, f"{op} -> {BOOLOP[type(node.op)].__name__}"


def apply_mutation(source, index):
    """Re-parse `source` fresh, mutate the node at position `index` in
    eligible_nodes() order, return the unparsed mutant source."""
    tree = ast.parse(source)
    nodes = eligible_nodes(tree)
    kind, node = nodes[index]
    if kind == "compare":
        node.ops = [BOUNDARY[type(node.ops[0])]()]
    elif kind == "boolconst":
        node.value = not node.value
    elif kind == "boolop":
        node.op = BOOLOP[type(node.op)]()
    return ast.unparse(ast.fix_missing_locations(tree))


def run_source(src, timeout, cwd=None, filename="mutant.py"):
    """Write src to filename INSIDE cwd (not /tmp) and run it from there.
    Many scripts in this estate use sys.path.insert(0, ".") or otherwise
    assume they are launched from their repo root; running the mutant from
    an unrelated directory makes it fail at import time regardless of the
    mutation, and every result would misreport as SURVIVED. Using the
    target's own directory and filename keeps relative imports and any
    sibling-file lookups working the same way they would for the real file."""
    target_dir = cwd or os.getcwd()
    path = os.path.join(target_dir, f".mutant_{os.getpid()}_{filename}")
    with open(path, "w") as f:
        f.write(src)
    try:
        p = subprocess.run([sys.executable, os.path.basename(path)],
                            capture_output=True, timeout=timeout, text=True,
                            cwd=target_dir)
        return p.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    finally:
        os.unlink(path)


def probe(path, timeout=30, cwd=None):
    source = open(path).read()
    tree = ast.parse(source, filename=path)
    target_dir = cwd or os.path.dirname(os.path.abspath(path)) or "."
    fname = os.path.basename(path)
    baseline = run_source(source, timeout, cwd=target_dir, filename=fname)

    nodes = eligible_nodes(tree)
    results = []
    for i, (kind, node) in enumerate(nodes):
        lineno, col, desc = describe(kind, node)
        try:
            mutant_src = apply_mutation(source, i)
        except Exception as e:
            results.append((lineno, desc, "ERROR", f"apply failed: {e}"))
            continue
        rc = run_source(mutant_src, timeout, cwd=target_dir, filename=fname)
        if rc == "TIMEOUT":
            verdict = "ERROR"
        elif rc == baseline:
            verdict = "SURVIVED"
        else:
            verdict = "KILLED"
        results.append((lineno, desc, verdict, f"exit {baseline!r} -> {rc!r}"))
    return baseline, results


def report(path, timeout=30, cwd=None):
    baseline, results = probe(path, timeout, cwd=cwd)
    killed = sum(1 for _, _, v, _ in results if v == "KILLED")
    survived = sum(1 for _, _, v, _ in results if v == "SURVIVED")
    errored = sum(1 for _, _, v, _ in results if v == "ERROR")
    total = killed + survived
    print(f"target        : {path}")
    print(f"baseline exit : {baseline}")
    print(f"mutation sites: {len(results)}")
    print()
    for lineno, desc, verdict, detail in results:
        print(f"  line {lineno:<4} {verdict:9s} {desc:20s} {detail}")
    print()
    if total:
        print(f"killed={killed} survived={survived} errored={errored} "
              f"score={killed/total:.1%}")
    else:
        print(f"killed={killed} survived={survived} errored={errored} score=n/a (0 scoreable sites)")
    if survived:
        print()
        print("SURVIVED mutants above did not change the exit code. Either the "
              "check does not depend on that comparison/constant, or the "
              "mutation landed somewhere unreachable from the verdict path. "
              "Read each one; a low score is a place to look, not a proven defect.")
    return baseline, results


# ---------------------------------------------------------------------------
# ANTI-VACUITY SELFTEST
# ---------------------------------------------------------------------------

DEPENDENT_FIXTURE = '''\
import sys
x = 5
if x >= 5:
    sys.exit(0)
sys.exit(1)
'''
# x=5: x>=5 True -> exit 0. Mutate >= to > : x>5 is False -> exit 1.
# Verdict changes -> must be KILLED. This is the shape a real boundary
# bug (off-by-one in a threshold check) would produce.

INDEPENDENT_FIXTURE = '''\
import sys
x = 5
if x >= 5:
    pass  # comparison result computed, then discarded
sys.exit(1)
'''
# The comparison's result is never used to choose the exit code. No mutation
# to it can change the outcome. Must be SURVIVED -- this is the shape of a
# guard that has no bearing on its own verdict, e.g. an assert that always
# runs but whose predicate nothing downstream depends on.


def selftest():
    print("=" * 68)
    print("ANTI-VACUITY SELFTEST")
    print("=" * 68)
    ok = True

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(DEPENDENT_FIXTURE)
        p1 = f.name
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(INDEPENDENT_FIXTURE)
        p2 = f.name

    try:
        print("\nFixture A (guard genuinely depends on its comparison):")
        _, res_a = report(p1)
        killed_a = sum(1 for _, _, v, _ in res_a if v == "KILLED")
        print(f"\n  requires >=1 KILLED: {'PASS' if killed_a >= 1 else 'FAIL'}")
        ok = ok and killed_a >= 1

        print("\n" + "-" * 68)
        print("\nFixture B (comparison computed but never used):")
        _, res_b = report(p2)
        survived_b = sum(1 for _, _, v, _ in res_b if v == "SURVIVED")
        print(f"\n  requires >=1 SURVIVED: {'PASS' if survived_b >= 1 else 'FAIL'}")
        ok = ok and survived_b >= 1
    finally:
        os.unlink(p1)
        os.unlink(p2)

    print("\n" + "=" * 68)
    if ok:
        print("SELFTEST PASS -- this tool reports both KILLED and SURVIVED "
              "depending on input. It is not stuck reporting one verdict.")
    else:
        print("SELFTEST FAIL -- do not trust output from this tool until fixed.")
    print("=" * 68)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", help="path to a .py file to mutation-test")
    ap.add_argument("--timeout", type=float, default=30)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--cwd", default=None,
                     help="run mutants from this directory instead of the "
                          "target file's own directory (needed for scripts "
                          "whose relative imports assume the repo root)")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.target:
        ap.error("target required unless --selftest")
    _, results = report(a.target, a.timeout, cwd=a.cwd)
    survived = sum(1 for _, _, v, _ in results if v == "SURVIVED")
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())

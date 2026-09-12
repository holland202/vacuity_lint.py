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
  KILLED    exit code changed from baseline, OR exit code matched but the
            mutant crashed (uncaught traceback) while baseline did not (or
            vice versa) -- the mutated line mattered here
  SURVIVED  exit code unchanged AND crash-state unchanged -> the check did
            not depend on it
  CRASHED   the mutant made the target die to an uncaught exception the
            baseline did not raise. EXCLUDED from numerator and denominator.
            The gate did not detect the change; the change broke the gate.
  INVALID   the mutant does not compile. EXCLUDED from both.
  ERROR     mutant did not even run (timeout, or unparse failure)

  score = KILLED / (KILLED + SURVIVED).  CRASHED, INVALID and ERROR are
  excluded from both sides of that fraction.

  exit 0 = every scoreable mutant was killed
  exit 1 = at least one survivor
  exit 2 = could not look: nothing was scoreable

MASKED-CRASH CONFOUND, found 2026-08-21 against a real target (sovereign-
suite/tools/calibrate_governance.py, note059 P4 follow-up): Python's default
exit status for an unhandled exception is 1. Any target whose own legitimate
"unhealthy"/"failed" exit code is *also* 1 -- which is nearly every target,
since 1 is the conventional Unix failure code -- can have a mutation that
completely destroys its behavior (crashes before ever reaching the real
verdict) score as SURVIVED, because exit-code comparison alone cannot tell
"correctly computed failure" from "blew up before computing anything."
Verified case: `out = args.out or f"..."` mutated to `and`; args.out is None
by default, so the mutant computes out=None, then `open(None, "w")` raises
an uncaught TypeError -- the report is never written, nothing downstream
runs -- and the crash's exit code (1) coincidentally equals the target's own
baseline "UNHEALTHY, exit 1" code. Old logic: SURVIVED. Fixed by also
comparing whether an uncaught traceback appears on stderr, independent of
the exit code.

CORRECTION 2026-09-12, kept rather than rewritten. From 2026-08-21 the fix
above classified masked crashes as KILLED. That was half right. Detecting
them was necessary; scoring them as detections was not. A mutant that makes
the target raise has not been caught by the target -- it has destroyed it,
and counting it in the numerator inflates the score. Crash mutants are now
their own excluded category.

Direction of the old error: INFLATION. Every score this tool printed before
2026-09-12 for a target with crash-inducing mutants is an UPPER BOUND on the
corrected score, never a lower one. No conclusion that rested on a LOW score
is weakened by this correction; such scores can only fall further. Scores
published before that date should be re-run before being quoted again.
report() now prints the corrected score and the pre-correction score side by
side from a single run, so a correction can be written without guessing.

A related defect does NOT apply to this tool, and the reason is structural
rather than lucky: mutants are executed as __main__ via
`python .mutant_<pid>_<name>.py`, and CPython does not read or write cached
bytecode for the main script. A sibling tool that instead mutates a MODULE
and lets a separate test suite import it IS affected -- apply_mutation()
round-trips through ast.unparse, so a mutant is often the same byte length
as the original and written in the same clock second, which defeats
CPython's (mtime, size) staleness check and silently runs the stale
original. Do not refactor this tool to import its target without deleting
the target's cached bytecode first.

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


def crashed(stderr):
    """True if stderr shows an uncaught Python exception, i.e. the process
    died via traceback rather than via a deliberate sys.exit/return path."""
    return "Traceback (most recent call last):" in stderr


def run_source(src, timeout, cwd=None, filename="mutant.py"):
    """Write src to filename INSIDE cwd (not /tmp) and run it from there.
    Many scripts in this estate use sys.path.insert(0, ".") or otherwise
    assume they are launched from their repo root; running the mutant from
    an unrelated directory makes it fail at import time regardless of the
    mutation, and every result would misreport as SURVIVED. Using the
    target's own directory and filename keeps relative imports and any
    sibling-file lookups working the same way they would for the real file.

    Returns (returncode, crashed_bool). crashed_bool distinguishes "exited
    via a deliberate code path" from "died to an uncaught exception" even
    when both happen to produce the same returncode -- see the MASKED-CRASH
    CONFOUND note in the module docstring."""
    target_dir = cwd or os.getcwd()
    path = os.path.join(target_dir, f".mutant_{os.getpid()}_{filename}")
    with open(path, "w") as f:
        f.write(src)
    try:
        p = subprocess.run([sys.executable, os.path.basename(path)],
                            capture_output=True, timeout=timeout, text=True,
                            cwd=target_dir)
        return p.returncode, crashed(p.stderr)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", False
    finally:
        os.unlink(path)


def probe(path, timeout=30, cwd=None):
    source = open(path).read()
    tree = ast.parse(source, filename=path)
    target_dir = cwd or os.path.dirname(os.path.abspath(path)) or "."
    fname = os.path.basename(path)
    baseline, baseline_crashed = run_source(source, timeout, cwd=target_dir, filename=fname)

    nodes = eligible_nodes(tree)
    results = []
    for i, (kind, node) in enumerate(nodes):
        lineno, col, desc = describe(kind, node)
        try:
            mutant_src = apply_mutation(source, i)
        except Exception as e:
            results.append((lineno, desc, "ERROR", f"apply failed: {e}"))
            continue
        try:
            compile(mutant_src, path, "exec")
        except SyntaxError as e:
            results.append((lineno, desc, "INVALID",
                            f"does not compile: {e.msg}"))
            continue
        rc, rc_crashed = run_source(mutant_src, timeout, cwd=target_dir, filename=fname)
        if rc == "TIMEOUT":
            verdict = "ERROR"
            detail = f"exit {baseline!r} -> TIMEOUT"
        elif rc_crashed and not baseline_crashed:
            # CORRECTED 2026-09-12. This branch used to yield KILLED, both
            # here and via the rc != baseline branch below. A mutant that
            # makes the module die to an uncaught exception has not been
            # DETECTED by the gate -- it has broken the gate. Counting it as
            # a kill inflates the numerator with crashes.
            verdict = "CRASHED"
            detail = (f"exit {baseline!r} -> {rc!r}  (uncaught exception "
                      f"introduced -- excluded, not a detection)")
        elif rc != baseline:
            verdict = "KILLED"
            detail = f"exit {baseline!r} -> {rc!r}"
        elif rc_crashed != baseline_crashed:
            verdict = "KILLED"
            detail = (f"exit {baseline!r} -> {rc!r}  (masked -- crash removed)")
        else:
            verdict = "SURVIVED"
            detail = f"exit {baseline!r} -> {rc!r}"
        results.append((lineno, desc, verdict, detail))
    return baseline, results


def report(path, timeout=30, cwd=None):
    baseline, results = probe(path, timeout, cwd=cwd)
    killed = sum(1 for _, _, v, _ in results if v == "KILLED")
    survived = sum(1 for _, _, v, _ in results if v == "SURVIVED")
    errored = sum(1 for _, _, v, _ in results if v == "ERROR")
    crashed_n = sum(1 for _, _, v, _ in results if v == "CRASHED")
    invalid = sum(1 for _, _, v, _ in results if v == "INVALID")
    total = killed + survived
    print(f"target        : {path}")
    print(f"baseline exit : {baseline}")
    print(f"mutation sites: {len(results)}")
    print()
    for lineno, desc, verdict, detail in results:
        print(f"  line {lineno:<4} {verdict:9s} {desc:20s} {detail}")
    print()
    print(f"counted  : killed={killed} survived={survived}")
    print(f"excluded : crashed={crashed_n} invalid={invalid} errored={errored}")
    if total:
        print(f"score    = {killed/total:.1%}   n = {total}")
    else:
        print(f"score    = n/a (0 scoreable sites)   n = 0")
    # Both numbers, from one run, so a correction can be written without
    # guessing what the old rule would have said. Pre-2026-09-12 this tool
    # counted crash mutants as kills.
    legacy_k = killed + crashed_n
    legacy_t = legacy_k + survived
    if legacy_t and crashed_n:
        print(f"score    = {legacy_k/legacy_t:.1%}   n = {legacy_t}   "
              f"<- what this tool reported BEFORE 2026-09-12, when crash "
              f"mutants were counted as kills. Superseded.")
    if crashed_n:
        print()
        print(f"{crashed_n} mutant(s) CRASHED: they made the target die to an "
              f"uncaught exception rather than being detected by it. Excluded "
              f"from numerator and denominator. A crash is information about "
              f"the code, not evidence the gate noticed anything.")
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

MASKED_CRASH_FIXTURE = '''\
import sys
value = None
label = "ok" if True else value.attr
sys.exit(1)
'''
# Baseline: the True branch runs, label="ok", no crash, then sys.exit(1)
# fires deliberately -> rc=1, no traceback. The file's ONE eligible site is
# that bare `True`. Mutated to False: the else-branch runs, value.attr on
# None raises an uncaught AttributeError -> Python's own crash exit status
# is ALSO 1. Same returncode as baseline, totally different behavior (the
# real verdict path never even runs). An exit-code-only comparison would
# report SURVIVED. This is the confound found 2026-08-21 against
# calibrate_governance.py's `args.out or f"..."` line.
#
# HISTORY, kept rather than rewritten. From 2026-08-21 to 2026-09-12 this
# fixture asserted KILLED, and the tool scored it in the numerator. That was
# wrong, and the error was inflation: the mutation was not DETECTED by the
# target, it BROKE the target. Detecting the confound was right; calling it
# a kill was not. The assertion is now CRASHED and such mutants are excluded
# from both numerator and denominator. Any score this tool printed before
# 2026-09-12 for a target with crash-inducing mutants is an upper bound on
# the corrected score, never a lower one.


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
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(MASKED_CRASH_FIXTURE)
        p3 = f.name

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

        print("\n" + "-" * 68)
        print("\nFixture C (mutation crashes into the SAME exit code as baseline):")
        _, res_c = report(p3)
        crashed_c = sum(1 for _, _, v, _ in res_c if v == "CRASHED")
        killed_c = sum(1 for _, _, v, _ in res_c if v == "KILLED")
        print(f"\n  requires >=1 CRASHED (masked crash detected, and NOT "
              f"counted as a kill): "
              f"{'PASS' if crashed_c >= 1 and killed_c == 0 else 'FAIL'}")
        ok = ok and crashed_c >= 1 and killed_c == 0
    finally:
        os.unlink(p1)
        os.unlink(p2)
        os.unlink(p3)

    print("\n" + "=" * 68)
    if ok:
        print("SELFTEST PASS -- this tool reports KILLED, SURVIVED and "
              "CRASHED depending on input. It does not mistake a masked "
              "crash for a survivor, and it does not count one as a kill. "
              "It is not stuck reporting one verdict.")
        print()
        print("NOT covered by any fixture: the 'crash removed' direction "
              "(a mutant that stops an already-crashing baseline from "
              "crashing). That branch is unexercised. Stated, not hidden.")
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
    killed = sum(1 for _, _, v, _ in results if v == "KILLED")
    if killed + survived == 0:
        # Added 2026-09-12. Previously this returned 0 -- a clean bill of
        # health -- for a run in which nothing was scoreable, e.g. every
        # mutant crashed or the file had no eligible sites. "Found nothing"
        # and "could not look" are different answers and must not share an
        # exit code. Same three-code scheme as vacuity_lint.py.
        sys.stderr.write("could not look: 0 scoreable sites (killed+survived "
                         "= 0). No score was measured.\n")
        return 2
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())

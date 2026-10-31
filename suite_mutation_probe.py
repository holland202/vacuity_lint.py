#!/usr/bin/env python3
"""
suite_mutation_probe.py v2 -- does a test suite actually constrain the code
it tests?

WHY THIS EXISTS
    mutation_probe.py (shipped alongside) mutates a script and runs THAT SAME
    SCRIPT: does the script's own verdict depend on its own comparisons?

    That is the wrong question for a project whose evidence looks like
    "1549/1549 developer suite, 1400/1400 adversarial, 28000/28000 property".
    There the code under test and the code that judges it are different files,
    so the question becomes:

        if I silently break the runtime, does the suite notice?

    A suite that passes 28,000 cases and also passes on broken code has not
    verified anything. This tool measures the difference, and prints its
    denominator, because a score without n is not a measurement.

WHAT CHANGED IN v2
    Built to a reporting spec that is not mine. Four changes, all requested:

    1. Crash and compile mutants no longer count as kills. v1 marked a mutant
       KILLED when the suite's crash state changed. That inflated the
       numerator with mutants that merely broke the module rather than being
       detected by the tests. They now go to their own bucket, excluded from
       BOTH numerator and denominator, with the exception type printed so
       they can be classified by hand.
    2. Every mutant prints its exact source diff, not just a line number.
    3. Suite stdout is captured and diffed, so the report says WHICH lines of
       the suite's output changed, not only whether the exit code moved.
    4. --verify-manifest checks a SHA-256 manifest before and after the run,
       so a sealed tree can be proven untouched.

    One more category exists because the data demanded it: SURVIVED_OUT means
    the suite's OUTPUT changed but its VERDICT did not. The tests saw the
    damage and still exited 0. It counts as a survivor.

VERDICTS
    KILLED       exit code changed, or the suite failed on an AssertionError
    SURVIVED     exit code and stdout both unchanged on broken code
    SURVIVED_OUT stdout changed, exit code did not. Still a survivor.
    CRASHED      mutant introduced an uncaught non-assertion exception.
                 EXCLUDED from the score. Not a meaningful kill.
    INVALID      mutant does not compile. EXCLUDED from the score.
    ERROR        timeout, or mutation could not be applied. EXCLUDED.

    denominator n = KILLED + SURVIVED + SURVIVED_OUT

EQUIVALENT MUTANTS
    Not detected automatically. Cannot be, in general -- it is undecidable.
    The per-mutant diff exists so survivors can be classified by hand. A
    survivor is evidence of a coverage or sensitivity gap, not proof of a
    production defect.

SAFETY
    This tool WRITES TO THE FILE GIVEN TO --source and restores it after every
    mutant, verifying each restore by SHA-256. Point it at a working copy,
    never at a sealed original. Use --verify-manifest to prove the sealed tree
    was untouched.

EXIT CODES
    0  ran, score >= --min-score
    1  ran, score <  --min-score
    2  could not look: baseline failed, no eligible sites, manifest mismatch

Zero dependencies. Standard library only. Python 3.8+.
"""

import argparse
import ast
import difflib
import hashlib
import math
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from mutation_probe import eligible_nodes, apply_mutation, describe
except ImportError:
    sys.stderr.write("suite_mutation_probe.py requires mutation_probe.py in "
                     "the same directory. Both ship together.\n")
    sys.exit(2)

EXC_RE = re.compile(r"^(\w*(?:Error|Exception))\b", re.M)


# ------------------------------------------------------------------ stats

def binom_upper(n, x, p):
    return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k)
               for k in range(x, n + 1))


def binom_lower(n, x, p):
    return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k)
               for k in range(0, x + 1))


def clopper_pearson(k, n, alpha=0.05):
    """Exact binomial interval, or (None, None) when there were no trials.

    CORRECTED 2026-09-14. This used to return (0.0, 1.0) for n == 0, which
    renders as an ordinary-looking "[0.0%, 100.0%]" and invites the reader to
    treat zero trials as a measured result. Zero trials is not a wide
    interval, it is the absence of one.

        NO MEASUREMENT != ZERO PERFORMANCE
    """
    if n == 0:
        return (None, None)
    lo, hi = 0.0, 1.0
    if k > 0:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if binom_upper(n, k, m) < alpha / 2:
                a = m
            else:
                b = m
        lo = (a + b) / 2
    if k < n:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if binom_lower(n, k, m) > alpha / 2:
                a = m
            else:
                b = m
        hi = (a + b) / 2
    return (lo, hi)


# ------------------------------------------------------------------ io

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_manifest(path):
    """Parse 'sha256  relpath' lines. Tolerates Get-FileHash CSV output."""
    entries = []
    base = os.path.dirname(os.path.abspath(path))
    for raw in open(path, "r", encoding="utf-8-sig"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "," in line:
            parts = [p.strip().strip('"') for p in line.split(",")]
            cand = [p for p in parts if re.fullmatch(r"[0-9a-fA-F]{64}", p)]
            rest = [p for p in parts if p not in cand and p]
            if cand and rest:
                entries.append((cand[0].lower(), rest[-1]))
            continue
        parts = line.split(None, 1)
        if len(parts) == 2 and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            entries.append((parts[0].lower(), parts[1].strip().lstrip("*")))
        elif len(parts) == 2 and re.fullmatch(r"[0-9a-fA-F]{64}", parts[1]):
            entries.append((parts[1].lower(), parts[0]))
    return base, entries


def verify_manifest(path, when):
    base, entries = read_manifest(path)
    if not entries:
        return ["manifest %s parsed to zero entries" % path]
    bad = []
    for want, rel in entries:
        p = rel if os.path.isabs(rel) else os.path.join(base, rel)
        if not os.path.isfile(p):
            bad.append("%s MISSING (%s)" % (rel, when))
            continue
        got = sha256(p)
        if got != want:
            bad.append("%s CHANGED (%s)\n    expected %s\n    actual   %s"
                       % (rel, when, want, got))
    return bad


def purge_bytecode(source_path):
    """Delete cached bytecode for the mutated module.

    This is not housekeeping. CPython invalidates a .pyc using the source
    file's (mtime, size). apply_mutation() round-trips through ast.unparse,
    so a mutant is frequently the SAME BYTE LENGTH as the original, and the
    write lands in the same clock second. Both checks then pass and the
    interpreter silently runs the STALE original while the mutated source
    sits on disk -- the suite passes, and the mutant is recorded as a
    survivor that was never actually executed.

    Measured, not theorised: without this, a boolean flip that provably
    raises NameError when run by hand was reported SURVIVED, output
    identical. Selftest fixture D is the regression test for it.
    """
    d = os.path.dirname(source_path)
    stem = os.path.splitext(os.path.basename(source_path))[0]
    cache = os.path.join(d, "__pycache__")
    if os.path.isdir(cache):
        for f in os.listdir(cache):
            if f.split(".")[0] == stem and f.endswith(".pyc"):
                try:
                    os.unlink(os.path.join(cache, f))
                except OSError:
                    pass
    legacy = os.path.join(d, stem + ".pyc")
    if os.path.isfile(legacy):
        try:
            os.unlink(legacy)
        except OSError:
            pass


def run_suite(command, cwd, timeout, source_path=None, extra_env=None):
    if source_path:
        purge_bytecode(source_path)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_env:
        env.update(extra_env)
    try:
        p = subprocess.run(command, shell=True, cwd=cwd, timeout=timeout,
                           capture_output=True, text=True, env=env)
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "", ""


def exception_type(stderr):
    """Exception class name from a traceback, or None."""
    if "Traceback (most recent call last)" not in stderr:
        return None
    hits = EXC_RE.findall(stderr)
    return hits[-1] if hits else "UnknownException"


def stdout_delta(base_out, mut_out, max_lines=4):
    """Which output lines changed. Returns (n_changed, sample_lines)."""
    a, b = base_out.splitlines(), mut_out.splitlines()
    changed = [l for l in difflib.unified_diff(a, b, n=0, lineterm="")
               if (l.startswith("+") or l.startswith("-"))
               and not l.startswith("+++") and not l.startswith("---")]
    return len(changed), changed[:max_lines]


def source_diff(original, mutant, name, context=1):
    out = []
    for line in difflib.unified_diff(original.splitlines(),
                                     mutant.splitlines(),
                                     fromfile=name, tofile=name + " (mutant)",
                                     n=context, lineterm=""):
        if line.startswith("+++") or line.startswith("---"):
            continue
        out.append(line)
    return out


# ------------------------------------------------------------ coverage

COVERAGE_STUB = r"""
# Written by suite_mutation_probe.py. Collects executed line numbers for ONE
# target file, in every Python process the suite starts, and appends them to
# a shared file. Imported automatically by CPython at interpreter startup
# because this directory is first on PYTHONPATH.
import atexit, os, sys
try:
    import threading
except Exception:
    threading = None

_TARGET = os.environ.get("SMP_COV_TARGET")
_OUT = os.environ.get("SMP_COV_OUT")
_seen = set()


def _tracer(frame, event, arg):
    if event == "line":
        try:
            if os.path.realpath(frame.f_code.co_filename) == _TARGET:
                _seen.add(frame.f_lineno)
        except Exception:
            pass
    return _tracer


def _flush():
    if not _seen:
        return
    try:
        with open(_OUT, "a") as fh:
            fh.write("".join("%d\n" % n for n in sorted(_seen)))
    except Exception:
        pass


def _log(kind, pid, detail=""):
    path = os.environ.get("SMP_ATTACH_LOG")
    if not path:
        return
    try:
        with open(path, "a") as fh:
            fh.write("%s %d %s\n" % (kind, pid, detail))
    except Exception:
        pass


def _looks_like_python(argv):
    try:
        head = argv[0] if isinstance(argv, (list, tuple)) else argv
        return "python" in os.path.basename(str(head)).lower()
    except Exception:
        return False


# Records every Python child this process starts.
# Deliberately DOES NOT re-inject the tracer into the child: re-injecting
# would change the behaviour of the suite under audit. This only observes.
# A Python child that starts and never attaches appears as a LAUNCH with no
# matching ATTACH, and reconciliation fails closed. That is the bounded
# guarantee -- attached, or the audit stops.
def _install_launch_recorder():
    try:
        import subprocess
    except Exception:
        return
    _real_popen_init = subprocess.Popen.__init__

    def _init(self, args, *a, **kw):
        _real_popen_init(self, args, *a, **kw)
        try:
            if _looks_like_python(args):
                _log("LAUNCH", self.pid, str(args)[:200])
        except Exception:
            pass

    subprocess.Popen.__init__ = _init

    for name in ("execv", "execve", "execvp", "execvpe"):
        real = getattr(os, name, None)
        if real is None:
            continue

        def _mk(real_fn):
            def _wrapped(path, args, *rest):
                try:
                    if _looks_like_python([path]):
                        _log("LAUNCH", os.getpid(), str(path)[:200])
                except Exception:
                    pass
                return real_fn(path, args, *rest)
            return _wrapped

        try:
            setattr(os, name, _mk(real))
        except Exception:
            pass


if _TARGET and _OUT:
    _log("ATTACH", os.getpid(), sys.executable)
    _install_launch_recorder()
    atexit.register(_flush)
    sys.settrace(_tracer)
    if threading is not None:
        threading.settrace(_tracer)
"""


def make_coverage_env(source_path, workdir):
    """Return (env_overrides, out_path). Injects a sitecustomize tracer."""
    stubdir = os.path.join(workdir, "_smp_cov")
    os.makedirs(stubdir, exist_ok=True)
    with open(os.path.join(stubdir, "sitecustomize.py"), "w") as f:
        f.write(COVERAGE_STUB)
    out = os.path.join(stubdir, "executed.txt")
    attach = os.path.join(stubdir, "attach.log")
    for f in (out, attach):
        if os.path.exists(f):
            os.unlink(f)

    # PATH shims: catch a Python started by a NON-Python parent (a shell
    # script, make, a test runner written in another language). The shim
    # records the launch and then execs the real interpreter, which keeps the
    # same pid, so the subsequent ATTACH reconciles against this LAUNCH.
    bindir = os.path.join(stubdir, "bin")
    os.makedirs(bindir, exist_ok=True)
    real_py = sys.executable
    for name in ("python", "python3", os.path.basename(real_py)):
        shim = os.path.join(bindir, name)
        with open(shim, "w") as f:
            f.write("#!/bin/sh\n"
                    'printf "LAUNCH %%d %%s\\n" "$$" "$0" >> "$SMP_ATTACH_LOG"\n'
                    'exec "%s" "$@"\n' % real_py)
        os.chmod(shim, 0o755)

    prior = os.environ.get("PYTHONPATH", "")
    env = {
        "PYTHONPATH": stubdir + (os.pathsep + prior if prior else ""),
        "SMP_COV_TARGET": os.path.realpath(source_path),
        "SMP_COV_OUT": out,
        "SMP_ATTACH_LOG": attach,
        "PATH": bindir + os.pathsep + os.environ.get("PATH", ""),
    }
    return env, out, attach


def reconcile_attachment(attach_path):
    """Every Python process launched must also have attached.

    Returns (ok, launched, attached, orphans). An orphan is a Python process
    that started and never reported the tracer -- an isolated or
    environment-sanitized child. Its coverage is invisible, so any
    NOT_EXERCISED verdict downstream would be unsound.
    """
    launched, attached = {}, set()
    if os.path.isfile(attach_path):
        for raw in open(attach_path):
            parts = raw.split(None, 2)
            if len(parts) < 2 or not parts[1].isdigit():
                continue
            kind, pid = parts[0], int(parts[1])
            if kind == "ATTACH":
                attached.add(pid)
            elif kind == "LAUNCH":
                launched[pid] = (parts[2].strip() if len(parts) > 2 else "")
    orphans = {p: d for p, d in launched.items() if p not in attached}
    return (not orphans), launched, attached, orphans


def reset_coverage_files(*paths):
    """Truncate the per-run coverage artifacts.

    The attach log is append-only within a run. Reconciling a mutant against
    a log that still holds the baseline's pids would compare the wrong two
    sets, so each run starts from empty.
    """
    for path in paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except OSError:
            pass


def read_executed(out_path):
    if not os.path.isfile(out_path):
        return set()
    lines = set()
    for raw in open(out_path):
        raw = raw.strip()
        if raw.isdigit():
            lines.add(int(raw))
    return lines


# ------------------------------------------------------ mutant identity

SCHEMA = "mutation-campaign"
SCHEMA_VERSION = "1.3.0"
TOOL_NAME = "suite_mutation_probe.py"
TOOL_SERIES = "2.5"

_HERE = os.path.abspath(__file__)


def _self_identity():
    """The version is a READING of this file's bytes, not a stored constant.

    v2.2 shipped two different binaries both declaring "2.2.0", because the
    constant was bumped by hand and bumped late. A constant a human keeps in
    sync with the file is the same class of claim as a filename: unverifiable,
    and wrong exactly when it matters. Hashing the file at import means the
    declared identity cannot separate from the content -- change one byte and
    the version changes with it, whether or not anyone remembered to.
    """
    try:
        return sha256(_HERE)
    except OSError:
        return None


SELF_SHA256 = _self_identity()
TOOL_VERSION = ("%s+%s" % (TOOL_SERIES, SELF_SHA256[:12]) if SELF_SHA256
                else "%s+UNVERIFIED" % TOOL_SERIES)


def _scope_chain(tree, target):
    """Qualified name of the function/class enclosing `target`, e.g.
    'AdmissionGate.check'. Empty string at module level."""
    best = []

    def walk(node, chain):
        for child in ast.iter_child_nodes(node):
            nxt = chain
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef)):
                nxt = chain + [child.name]
            if child is target:
                best.extend(nxt)
                return True
            if walk(child, nxt):
                return True
        return False

    walk(tree, [])
    return ".".join(best)


def _enclosing_stmt(tree, target):
    """Source text of the smallest statement containing `target`,
    normalised through ast.unparse so reformatting does not change it."""
    found = [None]

    def walk(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                if _contains(child, target):
                    found[0] = child
                    walk(child)
                    return
            else:
                walk(child)

    def _contains(node, tgt):
        if node is tgt:
            return True
        return any(_contains(c, tgt) for c in ast.iter_child_nodes(node))

    walk(tree)
    if found[0] is None:
        return ""
    try:
        # unparse the statement head only, not its whole body, so an edit
        # elsewhere in a long function does not move every mutant's id
        node = found[0]
        if isinstance(node, (ast.If, ast.While, ast.For, ast.With)):
            shallow = type(node)(**{f: getattr(node, f, None)
                                    for f in node._fields})
            shallow.body = [ast.Pass()]
            if hasattr(shallow, "orelse"):
                shallow.orelse = []
            ast.fix_missing_locations(shallow)
            return ast.unparse(shallow)
        return ast.unparse(node)
    except Exception:
        return ""


def mutant_identity(rel_source, tree, node, operator):
    """Deterministic id for a mutation site.

    IDENTITY SCHEME, stated so it can be argued with:
      sha256( relative source path | enclosing qualified scope |
              operator | normalised enclosing statement )[:16]

    Deliberately EXCLUDES the line number. A mutant keeps its id when code
    is inserted above it, when the file is reformatted, or when an unrelated
    part of the same function changes. It CHANGES when the mutated statement
    itself is edited, when the enclosing function is renamed, or when the
    file is moved -- which is correct: that is a different mutant, not the
    same one relocated.

    Known collision case, stated rather than hidden: two identical
    statements in the same scope with the same operator (e.g. `if a >= b:`
    twice in one function) produce the SAME id. A disambiguating ordinal is
    appended when that happens, so ids stay unique within a campaign, but
    the ordinal is position-dependent and will move if one of the twins is
    deleted. Rare, and preferable to smuggling line numbers back in.
    """
    scope = _scope_chain(tree, node)
    stmt = _enclosing_stmt(tree, node)
    raw = "|".join([rel_source, scope, operator, stmt])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], raw


# ------------------------------------------------------------------ probe

def probe(source_path, suite_cmd, cwd, timeout, sample, seed,
          manifest=None, verbose=True, show_diff=True, trace_mutants=True):
    source_path = os.path.abspath(source_path)
    if not os.path.isfile(source_path):
        raise FileNotFoundError(source_path)

    if manifest:
        bad = verify_manifest(manifest, "before run")
        if bad:
            return {"abort_code": "MANIFEST_MISMATCH",
                    "abort": "sealed manifest does not match before the run:"
                             "\n  " + "\n  ".join(bad)}
        if verbose:
            print("sealed manifest       : verified before run")

    original = open(source_path, "r", encoding="utf-8").read()
    original_hash = sha256(source_path)
    backup = source_path + ".mutbak"
    shutil.copy2(source_path, backup)

    def restore():
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(original)
        if sha256(source_path) != original_hash:
            sys.stderr.write("\nFATAL: could not restore %s. Untouched copy "
                             "is at %s -- move it back by hand.\n"
                             % (source_path, backup))
            sys.exit(2)

    try:
        if verbose:
            print("source under mutation : %s" % source_path)
            print("source sha256         : %s" % original_hash)
            print("suite command         : %s" % suite_cmd)
            print("suite cwd             : %s" % cwd)
            print()
            print("running suite unmutated (baseline)...")

        cov_env, cov_out, attach_log = make_coverage_env(source_path, cwd)
        base_rc, base_out, base_err = run_suite(suite_cmd, cwd, timeout,
                                               source_path, cov_env)
        executed = read_executed(cov_out)
        if base_rc == "TIMEOUT":
            return {"abort_code": "BASELINE_TIMEOUT",
                    "abort": "suite timed out at baseline after %ds." % timeout,
                    "baseline_rc": "TIMEOUT"}
        if base_rc != 0:
            return {"abort_code": "BASELINE_FAILED",
                    "abort": "suite exited %r at baseline (expected 0). The "
                             "oracle must reproduce before mutation." % base_rc,
                    "baseline_rc": base_rc}
        # v2.5: THE SUITE MUST REPRODUCE ITSELF BEFORE IT CAN JUDGE ANYTHING.
        # Mutation testing runs the suite once per mutant. A suite that is not
        # re-runnable -- one that writes state on the first run and refuses or
        # fails on the second -- returns non-zero for every mutant after the
        # first, for reasons that have nothing to do with the mutation. Every
        # one of those is scored KILLED. The campaign then reports a near
        # perfect mutation score built almost entirely of artifact.
        #
        # This is the inverse of the coverage artifact found in SKN: that one
        # made a target look worse than the evidence warranted, this one makes
        # it look better. Detecting it is cheap -- run the baseline twice.
        # Resetting an arbitrary working tree is not decidable in general, so
        # the tool refuses rather than guessing how to clean up after a suite.
        reset_coverage_files(cov_out, attach_log)
        base2_rc, base2_out, _ = run_suite(suite_cmd, cwd, timeout,
                                           source_path, cov_env)
        if base2_rc != base_rc:
            return {"abort_code": "SUITE_NOT_REPRODUCIBLE",
                    "abort": "the suite is NOT RE-RUNNABLE. Two consecutive "
                             "unmutated runs returned different exit codes "
                             "(%r then %r) with no mutation between them. "
                             "Mutation testing runs this suite once per "
                             "mutant, so every mutant after the first would "
                             "inherit that second exit code and be scored "
                             "KILLED for a reason that is not the mutation. "
                             "That inflates the score instead of deflating "
                             "it. Refusing to measure. Make the suite "
                             "idempotent, or give the audit a reset step "
                             "that restores the tree between runs."
                             % (base_rc, base2_rc),
                    "baseline_rc": base_rc, "baseline_rc_second": base2_rc}
        stdout_stable = (base2_out == base_out)
        executed = read_executed(cov_out) or executed

        base_exc = exception_type(base_err)
        ok_attach, launched, attached, orphans = \
            reconcile_attachment(attach_log)
        if not ok_attach:
            detail = "\n  ".join("pid %d: %s" % (p, d or "(unknown)")
                                 for p, d in sorted(orphans.items()))
            return {"abort_code": "TOPOLOGY_UNQUALIFIED", "abort":
                    "TOPOLOGY QUALIFICATION FAILED. %d Python process(es) ran "
                    "during the baseline without the tracer attached, so their "
                    "coverage is invisible and every NOT_EXERCISED verdict "
                    "below would be unsound:\n  %s\n"
                    "Attached: %d. Launched: %d. A child started with a "
                    "sanitised environment, or an interpreter reached by a "
                    "path this audit cannot observe, will land here. Fix the "
                    "topology or narrow the audit command; do not proceed."
                    % (len(orphans), detail, len(attached), len(launched))}
        if not executed:
            return {"abort_code": "NO_COVERAGE", "abort":
                    "coverage instrumentation collected ZERO executed lines "
                    "for %s. Either the suite never imports it, or the suite "
                    "is not a Python process and the tracer could not attach. "
                    "Refusing to continue: without coverage every site would "
                    "be reported NOT_EXERCISED, which is indistinguishable "
                    "from a clean result and is exactly the ambiguity this "
                    "instrumentation exists to remove."
                    % os.path.basename(source_path)}
        if verbose:
            print("baseline              : exit 0, %d line(s) of output, no "
                  "uncaught traceback" % len(base_out.splitlines()))
            print("coverage              : %d line(s) of the target executed "
                  "by the suite" % len(executed))
            print("attachment            : %d python process(es) attached, "
                  "%d launched, 0 orphaned"
                  % (len(attached), len(launched)))
            print()

        tree = ast.parse(original, filename=source_path)
        nodes = eligible_nodes(tree)
        total_sites = len(nodes)
        if total_sites == 0:
            return {"abort_code": "NO_SITES",
                    "abort": "no eligible mutation sites in %s."
                             % os.path.basename(source_path)}

        indices = list(range(total_sites))
        sampled = False
        if sample and sample < total_sites:
            random.Random(seed).shuffle(indices)
            indices = sorted(indices[:sample])
            sampled = True

        if verbose:
            print("eligible sites        : %d" % total_sites)
            if sampled:
                print("sampled               : %d (seed %d)"
                      % (len(indices), seed))
            print("suite runs to do      : %d" % len(indices))
            print()

        rel_source = os.path.relpath(source_path, cwd)
        try:
            normalised_original = ast.unparse(ast.parse(original))
        except Exception:
            normalised_original = original
        seen_ids = {}
        results = []
        for n, i in enumerate(indices, 1):
            kind, node = nodes[i]
            lineno, col, desc = describe(kind, node)
            mid, mid_raw = mutant_identity(rel_source, tree, node, desc)
            if mid in seen_ids:
                seen_ids[mid] += 1
                mid = "%s#%d" % (mid, seen_ids[mid])
            else:
                seen_ids[mid] = 0
            line_end = getattr(node, "end_lineno", lineno) or lineno
            try:
                mutant = apply_mutation(original, i)
            except Exception as e:
                results.append(dict(line=lineno, line_end=line_end, desc=desc,
                                    mutant_id=mid, id_inputs=mid_raw,
                                    verdict="ERROR",
                                    detail="apply failed: %s" % e, diff=[],
                                    out_changed=[], rc=None, exc=None,
                                    exc_msg=None, n_changed=0))
                continue

            # Diff normalised-vs-normalised. apply_mutation round-trips the
            # whole file through ast.unparse, so diffing against the raw
            # original buries the one real change under blank-line and
            # formatting noise from every other line in the file. Both sides
            # normalised isolates the mutation. Line numbers elsewhere in the
            # record refer to the ORIGINAL file, not to this normalised form.
            diff = source_diff(normalised_original, mutant,
                               os.path.basename(source_path))

            if lineno not in executed:
                # The suite never ran this line. A mutation here could not
                # possibly have been detected, so calling it SURVIVED would
                # blame the suite for a gap it was never given the chance to
                # cover. Excluded from both sides of the score.
                results.append(dict(line=lineno, line_end=line_end, desc=desc,
                                    mutant_id=mid, id_inputs=mid_raw,
                                    verdict="NOT_EXERCISED",
                                    detail="line %d never executed by the "
                                           "suite; mutant not run" % lineno,
                                    diff=diff, out_changed=[], rc=None,
                                    exc=None, exc_msg=None, n_changed=0))
                if verbose:
                    print("[%d/%d] line %-5d %-13s %-22s %s"
                          % (n, len(indices), lineno, "NOT_EXERCISED", desc,
                             "never executed -- excluded"))
                    print()
                continue
            try:
                compile(mutant, source_path, "exec")
            except SyntaxError as e:
                results.append(dict(line=lineno, line_end=line_end, desc=desc,
                                    mutant_id=mid, id_inputs=mid_raw,
                                    verdict="INVALID",
                                    detail="does not compile: %s" % e.msg,
                                    diff=diff, out_changed=[], rc=None,
                                    exc="SyntaxError", exc_msg=e.msg,
                                    n_changed=0))
                continue

            with open(source_path, "w", encoding="utf-8") as f:
                f.write(mutant)
            if trace_mutants:
                # v2.4: the mutant runs in the SAME environment as the
                # baseline. Before this, the baseline carried sys.settrace, a
                # modified PATH and a modified PYTHONPATH and the mutants did
                # not, so every verdict was a comparison between one traced
                # run and a set of untraced ones. Found by Graeme Randle.
                reset_coverage_files(cov_out, attach_log)
                rc, out, err = run_suite(suite_cmd, cwd, timeout,
                                         source_path, cov_env)
                m_ok, m_launched, m_attached, m_orphans = \
                    reconcile_attachment(attach_log)
            else:
                rc, out, err = run_suite(suite_cmd, cwd, timeout, source_path)
                m_ok, m_launched, m_attached, m_orphans = True, {}, set(), {}
            restore()

            exc = exception_type(err)
            n_changed, sample_lines = stdout_delta(base_out, out)

            if rc == "TIMEOUT":
                verdict, detail = "ERROR", "exit 0 -> TIMEOUT"
            elif not m_ok:
                # The baseline reconciled with zero orphans, so an orphan here
                # is new: the mutation changed the process topology. The
                # kill/survive verdict is not known to be wrong -- it rests on
                # exit code and stdout, both still observed -- but this run is
                # outside the topology that was qualified before the campaign
                # began, and the qualification is what licensed the campaign.
                # Excluded rather than scored.
                verdict = "TOPOLOGY_CHANGED"
                detail = ("mutation introduced %d unattached python "
                          "process(es) (%s); outside the baseline-qualified "
                          "topology, excluded"
                          % (len(m_orphans),
                             ", ".join("pid %d" % q
                                       for q in sorted(m_orphans))))
            elif exc and exc != base_exc and exc != "AssertionError":
                verdict = "CRASHED"
                detail = ("%s raised (exit %r) -- excluded, not a meaningful "
                          "kill" % (exc, rc))
            elif rc != base_rc:
                verdict = "KILLED"
                detail = "exit 0 -> %r%s" % (rc, ", %s" % exc if exc else "")
            elif n_changed:
                verdict = "SURVIVED_OUT"
                detail = ("exit stayed 0, but %d output line(s) changed"
                          % n_changed)
            else:
                verdict, detail = "SURVIVED", "exit 0 -> 0, output identical"

            exc_msg = None
            if exc:
                tail = [l for l in err.strip().splitlines() if l.strip()]
                if tail:
                    exc_msg = tail[-1][:300]
            results.append(dict(line=lineno, line_end=line_end, desc=desc,
                                mutant_id=mid, id_inputs=mid_raw,
                                verdict=verdict, detail=detail, diff=diff,
                                out_changed=sample_lines,
                                rc=(None if rc == "TIMEOUT" else rc),
                                exc=exc, exc_msg=exc_msg,
                                n_changed=n_changed,
                                attached=len(m_attached),
                                launched=len(m_launched),
                                orphans=len(m_orphans)))

            if verbose:
                print("[%d/%d] line %-5d %-13s %-22s %s"
                      % (n, len(indices), lineno, verdict, desc, detail))
                if show_diff:
                    for d in diff:
                        print("        %s" % d)
                for s in sample_lines:
                    print("        suite output: %s" % s[:100])
                print()
    finally:
        restore()
        if os.path.exists(backup):
            os.unlink(backup)

    if manifest:
        bad = verify_manifest(manifest, "after run")
        if bad:
            return {"abort_code": "TREE_MODIFIED",
                    "abort": "SEALED TREE WAS MODIFIED during the run:\n  "
                             + "\n  ".join(bad)}
        if verbose:
            print("sealed manifest       : verified unchanged after run")
            print()

    return {"results": results, "total_sites": total_sites,
            "sampled": sampled, "seed": seed,
            "source_path": source_path, "rel_source": rel_source,
            "suite_cmd": suite_cmd, "cwd": cwd,
            "baseline_rc": base_rc,
            "executed_lines": sorted(executed),
            "attached": len(attached), "launched": len(launched),
            "trace_mutants": trace_mutants,
            "stdout_stable": stdout_stable,
            "sha_before": original_hash,
            "sha_after": sha256(source_path)}


def summarise(out, verbose=True):
    r = out["results"]

    def c(v):
        return sum(1 for x in r if x["verdict"] == v)

    killed, surv, surv_out = c("KILLED"), c("SURVIVED"), c("SURVIVED_OUT")
    crashed, invalid, errored = c("CRASHED"), c("INVALID"), c("ERROR")
    unexercised = c("NOT_EXERCISED")
    topology = c("TOPOLOGY_CHANGED")
    survivors = surv + surv_out
    n = killed + survivors
    # n == 0 means nothing was measured. Do NOT coerce that to 0.0; the JSON
    # path has always emitted null here and the console disagreed with it.
    score = (100.0 * killed / n) if n else None
    lo, hi = clopper_pearson(killed, n)

    if verbose:
        print("=" * 70)
        print("counted   : killed=%d survived=%d survived_out=%d"
              % (killed, surv, surv_out))
        print("excluded  : not_exercised=%d crashed=%d invalid=%d errored=%d"
              " topology_changed=%d"
              % (unexercised, crashed, invalid, errored, topology))
        print("denominator n = %d  (of %d eligible sites%s)"
              % (n, out["total_sites"],
                 ", sampled seed %d" % out["seed"] if out["sampled"] else ""))
        if score is None:
            print("mutation score = NO_MEASUREMENT   (n = 0)")
            print("                 Not zero percent. Nothing was measured:")
            print("                 no mutant was both executed and resolved.")
        else:
            print("mutation score = %.1f%%   95%% CI [%.1f%%, %.1f%%]"
                  % (score, 100 * lo, 100 * hi))
        if unexercised:
            print()
            print("%d site(s) NOT_EXERCISED: the suite never ran those lines, "
                  "so a mutation there could not have been detected. Excluded "
                  "from both numerator and denominator. This is a COVERAGE "
                  "gap, not a sensitivity gap, and the two must not be "
                  "reported as one number." % unexercised)
        if topology:
            print()
            print("%d mutant(s) changed the PROCESS TOPOLOGY: they started a "
                  "python process that the tracer could not attach to, which "
                  "the baseline did not. Excluded from both numerator and "
                  "denominator -- the run is outside the topology qualified "
                  "before the campaign, so it is not evidence either way."
                  % topology)
        if crashed:
            print()
            print("%d mutant(s) CRASHED and were excluded from both numerator "
                  "and denominator. A mutant that breaks the module is not "
                  "evidence that the tests detected anything." % crashed)
        if n and n < 10:
            print()
            print("WARNING: n = %d. That interval spans most of the unit "
                  "line. Report it with its denominator or not at all." % n)
        if surv_out:
            print()
            print("%d mutant(s) changed the suite's OUTPUT without changing "
                  "its VERDICT. The tests saw the damage and still exited 0. "
                  "Read those first." % surv_out)
        if survivors:
            print()
            print("%d survivor(s) above, each with its source diff. A "
                  "survivor is a coverage or sensitivity gap, not a proven "
                  "production defect -- classify equivalents by hand."
                  % survivors)
        print("=" * 70)
    return dict(topology=topology,
                score=score, status=("NO_MEASUREMENT" if n == 0 else "MEASURED"),
                killed=killed, survivors=survivors, n=n,
                survived=surv, survived_out=surv_out,
                crashed=crashed, invalid=invalid, errored=errored,
                unexercised=unexercised)


# ------------------------------------------------------------- json out

def _component_hashes():
    here = os.path.abspath(__file__)
    ops = os.path.join(os.path.dirname(here), "mutation_probe.py")
    out = {os.path.basename(here): sha256(here)}
    if os.path.isfile(ops):
        out[os.path.basename(ops)] = sha256(ops)
    return out


def build_abort_campaign(out, source_path, suite_cmd, cwd, manifest_path=None):
    """An abort is a result, and it must leave a file behind.

    Until v2.5 an aborted run returned exit 2 and printed to stderr, and that
    was all. The single most consequential outcome this instrument produces --
    "I refused to measure, and here is why" -- was the one outcome with no
    machine-readable artifact, so it could only be relayed by retyping it.
    A hand-copied result is a claim. This writes the same evidence an ordinary
    campaign writes, minus the numbers that were never earned.
    """
    src = os.path.abspath(source_path)
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "result": "ABORTED",
        "instrument": {
            "name": TOOL_NAME, "version": TOOL_VERSION,
            "series": TOOL_SERIES, "sha256": SELF_SHA256,
            "components": _component_hashes(),
        },
        "abort": {
            "code": out.get("abort_code", "UNSPECIFIED"),
            "reason": out.get("abort"),
            "baseline_rc": out.get("baseline_rc"),
            "baseline_rc_second": out.get("baseline_rc_second"),
        },
        "campaign": {
            "target": os.path.basename(src),
            "target_path": src,
            "target_sha256": (sha256(src) if os.path.isfile(src) else None),
            "suite_command": suite_cmd,
            "cwd": os.path.abspath(cwd),
            "interpreter": sys.executable,
            "interpreter_version": platform.python_version(),
            "platform": "%s %s" % (platform.system(), platform.machine()),
            "sealed_manifest": manifest_path,
        },
        "summary": {
            "mutation_score": None,
            "status": "NO_MEASUREMENT",
            "denominator": 0,
            "note": "The run aborted before any mutation was applied or "
                    "scored. This is not a score of zero and must not be "
                    "reported as one.",
        },
        "mutants": [],
    }


def build_campaign(out, manifest_path=None):
    """Assemble the JSON campaign object.

    EVIDENCE ONLY. Every field below is an observation: what was changed,
    what the suite did, what it printed, what it raised. There is
    deliberately no field for WHY a mutant survived. That is a downstream
    hypothesis and does not belong in an instrument's output.
    """
    r = out["results"]

    def c(v):
        return sum(1 for x in r if x["verdict"] == v)

    killed, surv, surv_out = c("KILLED"), c("SURVIVED"), c("SURVIVED_OUT")
    crashed, invalid, errored = c("CRASHED"), c("INVALID"), c("ERROR")
    unexercised = c("NOT_EXERCISED")
    topology = c("TOPOLOGY_CHANGED")
    n = killed + surv + surv_out
    score = (100.0 * killed / n) if n else None
    lo, hi = clopper_pearson(killed, n)

    here = os.path.abspath(__file__)
    ops = os.path.join(os.path.dirname(here), "mutation_probe.py")
    components = {os.path.basename(here): sha256(here)}
    if os.path.isfile(ops):
        components[os.path.basename(ops)] = sha256(ops)

    mutants = []
    for x in r:
        mutants.append({
            "mutant_id": x["mutant_id"],
            "mutant_id_inputs": x["id_inputs"],
            "mutation_operator": x["desc"],
            "source_file": out["rel_source"],
            "source_diff": "\n".join(x["diff"]),
            "line_start": x["line"],
            "line_end": x["line_end"],
            "baseline_exit_code": out["baseline_rc"],
            "mutant_exit_code": x["rc"],
            "classification": x["verdict"],
            "output_changed": bool(x["n_changed"]),
            "output_diff": "\n".join(x["out_changed"] or []),
            "exception_type": x["exc"],
            "exception_message": x["exc_msg"],
            "python_processes_attached": x.get("attached"),
            "python_processes_launched": x.get("launched"),
            "attachment_orphans": x.get("orphans"),
        })

    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "instrument": {
            "name": TOOL_NAME,
            "version": TOOL_VERSION,
            "sha256": sha256(here),
            "components": components,
            "source_diff_basis": "ast-normalised original vs ast-normalised "
                                 "mutant, so the diff isolates the mutation; "
                                 "line_start/line_end refer to the original "
                                 "file",
            "mutant_id_scheme": "sha256(relpath|scope|operator|normalised "
                                "enclosing statement)[:16]; line-number "
                                "independent; '#k' suffix disambiguates "
                                "identical twins in one scope",
        },
        "campaign": {
            "source_file": out["rel_source"],
            "suite_command": out["suite_cmd"],
            "working_directory": out["cwd"],
            "baseline_exit_code": out["baseline_rc"],
            "baseline_passed": out["baseline_rc"] == 0,
            "sealed_source_sha256_before": out["sha_before"],
            "sealed_source_sha256_after": out["sha_after"],
            "sealed_source_restored": out["sha_before"] == out["sha_after"],
            "manifest_verified": bool(manifest_path),
            "eligible_sites": out["total_sites"],
            "coverage_instrumented": True,
            "python_processes_attached": out.get("attached", 0),
            "python_processes_launched": out.get("launched", 0),
            "attachment_orphans": 0,
            "mutants_run_traced": out.get("trace_mutants", False),
            "environment_parity": ("baseline and mutants ran in the same "
                                   "environment" if out.get("trace_mutants")
                                   else "CONFOUNDED: baseline ran traced, "
                                        "mutants ran untraced; verdicts "
                                        "compare unlike runs"),
            "not_exercised_basis": ("baseline coverage only; the question is "
                                    "whether the suite exercises the ORIGINAL "
                                    "line, so this is not recomputed per "
                                    "mutant"),
            "target_lines_executed_by_suite": len(out.get("executed_lines", [])),
            "sampled": out["sampled"],
            "sample_seed": out["seed"] if out["sampled"] else None,
        },
        "mutants": mutants,
        "summary": {
            "killed": killed,
            "survived": surv,
            "survived_out": surv_out,
            "not_exercised": unexercised,
            "crashed": crashed,
            "invalid": invalid,
            "error": errored,
            "topology_changed": topology,
            "denominator": n,
            "status": "NO_MEASUREMENT" if n == 0 else "MEASURED",
            "mutation_score": score,
            "confidence_interval_low": (100.0 * lo) if lo is not None else None,
            "confidence_interval_high": (100.0 * hi) if hi is not None else None,
            "confidence_level": 0.95,
            "excluded_from_score": ["NOT_EXERCISED", "CRASHED", "INVALID",
                                    "ERROR", "TOPOLOGY_CHANGED"],
        },
    }


# ------------------------------------------------------------------ selftest

MOD_PLAIN = "def check(temp, ceiling):\n    return temp <= ceiling\n"

MOD_CRASHY = ("def check(temp, ceiling):\n"
              "    if True:\n"
              "        return temp <= ceiling\n"
              "    return _undefined_helper(temp)\n")

S_CHECKS = ("import sys, target_module as t\n"
            "ok = t.check(10, 10) is True and t.check(11, 10) is False\n"
            "sys.exit(0 if ok else 1)\n")

# CORRECTED 2026-09-13 by the coverage instrumentation, which is the point.
# This fixture used to read `assert callable(t.check)` and never call check()
# at all. Under v2.1 that reported SURVIVED, and v2.1 was WRONG: the suite
# had not failed to detect the mutation, it had never executed the mutated
# line. The tool was reporting a coverage gap as a sensitivity gap inside its
# own selftest. The fixture now calls check() and ignores the result, which
# is the theatre case it was always meant to represent.
S_THEATRE = ("import sys, target_module as t\n"
             "t.check(10, 10)\n"
             "t.check(11, 10)\n"
             "print('1000/1000 PASS')\n"
             "sys.exit(0)\n")

S_NOISY = ("import sys, target_module as t\n"
           "print('boundary at ceiling ->', t.check(10, 10))\n"
           "print('1000/1000 PASS')\n"
           "sys.exit(0)\n")

S_CRASHY = ("import sys, target_module as t\n"
            "print(t.check(10, 10))\n"
            "sys.exit(0)\n")

S_FAILING = "import sys\nsys.exit(1)\n"

# Fixture F: two comparison sites. The suite calls exercised() and never
# calls dormant(). A correct instrument must report them DIFFERENTLY.
MOD_PARTIAL = ("def exercised(a, b):\n"
               "    return a <= b\n"
               "\n"
               "def dormant(a, b):\n"
               "    return a >= b\n")

# Fixtures G and H qualify the TOPOLOGY, not the suite. G starts an honest
# Python child that inherits the environment and therefore attaches. H starts
# one with the environment stripped, which cannot attach -- its coverage is
# invisible, so every NOT_EXERCISED verdict downstream would be unsound and
# the audit must refuse to produce one.
S_MULTIPROC = ("import sys, subprocess, target_module as t\n"
               "r = subprocess.run([sys.executable, '-c',\n"
               "    'import target_module as t; assert t.check(1,1)'],\n"
               "    capture_output=True)\n"
               "ok = t.check(1,1) is True and t.check(2,1) is False\n"
               "sys.exit(0 if (ok and r.returncode == 0) else 1)\n")

S_SANITIZED = ("import sys, os, subprocess, target_module as t\n"
               "env = {'PATH': '/usr/bin:/bin', 'PYTHONPATH': ''}\n"
               "subprocess.run([sys.executable, '-c',\n"
               "    \"import sys; sys.path.insert(0,'.'); import target_module\"],\n"
               "    capture_output=True, env=env, cwd=os.getcwd())\n"
               "ok = t.check(1,1) is True and t.check(2,1) is False\n"
               "sys.exit(0 if ok else 1)\n")

# Fixture I: the ENVIRONMENT PARITY control. The suite prints whether the
# coverage tracer is present. Before v2.4 the baseline ran traced and every
# mutant ran untraced, so that line differed on every single mutant and the
# tool reported SURVIVED_OUT -- an artifact of the instrument, not a property
# of the suite. Run with trace_mutants=True it must read SURVIVED; run with
# trace_mutants=False the old defect must reappear as SURVIVED_OUT. A fixture
# that only passes in one direction would not prove the fix.
S_ENVPARITY = ("import os, sys, target_module as t\n"
               "print('tracer:', 'on' if os.environ.get('SMP_COV_TARGET')\n"
               "      else 'off')\n"
               "t.check(10, 10)\n"
               "t.check(11, 10)\n"
               "print('1000/1000 PASS')\n"
               "sys.exit(0)\n")

# Fixture J: the PER-MUTANT TOPOLOGY control. Baseline does not spawn, so the
# baseline reconciles clean. Flipping ISOLATE to True makes the target start a
# python child with a sanitised environment, which cannot attach. The suite
# never notices -- it still exits 0 -- so before v2.4 this scored as a plain
# SURVIVED. It is not a survivor; it is a run outside the qualified topology.
MOD_TOPOLOGY = ("import subprocess, sys\n"
                "\n"
                "ISOLATE = False\n"
                "\n"
                "\n"
                "def check(temp, ceiling):\n"
                "    if ISOLATE:\n"
                "        subprocess.run([sys.executable, '-c', 'pass'],\n"
                "                       capture_output=True,\n"
                "                       env={'PATH': '/usr/bin:/bin',\n"
                "                            'PYTHONPATH': ''})\n"
                "    return temp <= ceiling\n")

# Fixture L: the RE-RUNNABILITY control. S_ONESHOT passes once and refuses the
# second time, the shape of a sealed single-shot pipeline. Without the double
# baseline every mutant after the first inherits that refusal and is scored
# KILLED, so the campaign reports a near-perfect score made of artifact.
# S_IDEMPOTENT is the same suite with the state cleaned up, and must still be
# measurable -- otherwise the control would just be refusing everything.
S_ONESHOT = ("import os, sys, target_module as t\n"
             "marker = 'ONESHOT_RAN'\n"
             "if os.path.exists(marker):\n"
             "    sys.stderr.write('NO_AUTOMATIC_RETRY\\n')\n"
             "    sys.exit(1)\n"
             "open(marker, 'w').write('x')\n"
             "ok = t.check(10, 10) is True and t.check(11, 10) is False\n"
             "sys.exit(0 if ok else 1)\n")

S_IDEMPOTENT = ("import os, sys, target_module as t\n"
                "marker = 'ONESHOT_RAN'\n"
                "open(marker, 'w').write('x')\n"
                "ok = t.check(10, 10) is True and t.check(11, 10) is False\n"
                "os.remove(marker)\n"
                "sys.exit(0 if ok else 1)\n")

S_PARTIAL = ("import sys, target_module as t\n"
             "ok = t.exercised(1, 1) is True and t.exercised(2, 1) is False\n"
             "sys.exit(0 if ok else 1)\n")


def _abort_record_control(passes):
    """Fixture N: an abort must leave a machine-readable record.

    Before v2.5 an aborted run printed to stderr and returned 2, so the most
    consequential outcome the tool produces had no artifact and could only be
    relayed by retyping. A retyped result is a claim, not evidence.
    """
    import tempfile
    print("-" * 70)
    print("Fixture N  an abort writes a campaign record (EVIDENCE CONTROL)")
    ok = False
    with tempfile.TemporaryDirectory() as d:
        mod = os.path.join(d, "target_module.py")
        open(mod, "w").write(MOD_PLAIN)
        open(os.path.join(d, "suite.py"), "w").write(S_ONESHOT)
        cmd = "%s suite.py" % sys.executable
        out = probe(mod, cmd, d, 30, None, 0, verbose=False, show_diff=False)
        if "abort" not in out:
            print("  did not abort -- control cannot be evaluated")
        else:
            camp = build_abort_campaign(out, mod, cmd, d)
            need = [("result", camp.get("result") == "ABORTED"),
                    ("abort.code", bool(camp["abort"]["code"])),
                    ("abort.reason", bool(camp["abort"]["reason"])),
                    ("target_sha256", bool(camp["campaign"]["target_sha256"])),
                    ("suite_command", camp["campaign"]["suite_command"] == cmd),
                    ("interpreter", bool(camp["campaign"]["interpreter"])),
                    ("score is null", camp["summary"]["mutation_score"]
                     is None),
                    ("status NO_MEASUREMENT",
                     camp["summary"]["status"] == "NO_MEASUREMENT")]
            for name, good in need:
                print("  %-24s : %s" % (name, "yes" if good else "NO"))
            print("  abort code recorded      : %s" % camp["abort"]["code"])
            ok = all(g for _, g in need) and \
                camp["abort"]["code"] == "SUITE_NOT_REPRODUCIBLE"
    print("  -> %s" % ("PASS" if ok else "FAIL"))
    print()
    passes.append(ok)


def _identity_control(passes):
    """Fixture K: the instrument's declared version must be a reading of its
    own bytes. Copy this file, add one comment line, import the copy, and the
    declared version must move. If someone replaces the derivation with a
    hand-maintained constant, the copy declares the same version as the
    original and this fails -- which is the v2.2 defect reproduced on demand.
    """
    import tempfile
    import importlib.util
    print("-" * 70)
    print("Fixture K  declared version derives from content (IDENTITY "
          "SABOTAGE CONTROL)")
    anchored = bool(SELF_SHA256) and TOOL_VERSION.endswith(SELF_SHA256[:12])
    drifted = None
    try:
        with tempfile.TemporaryDirectory() as d:
            twin = os.path.join(d, "twin_probe.py")
            shutil.copy2(_HERE, twin)
            with open(twin, "a", encoding="utf-8") as f:
                f.write("\n# one comment line of drift\n")
            ops = os.path.join(os.path.dirname(_HERE), "mutation_probe.py")
            if os.path.isfile(ops):
                shutil.copy2(ops, os.path.join(d, "mutation_probe.py"))
            sys.path.insert(0, d)
            try:
                spec = importlib.util.spec_from_file_location("twin_probe",
                                                             twin)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                drifted = mod.TOOL_VERSION
            finally:
                sys.path.remove(d)
    except Exception as e:
        print("  could not build the twin: %s" % e)
    moved = bool(drifted) and drifted != TOOL_VERSION
    same_series = bool(drifted) and \
        drifted.split("+")[0] == TOOL_VERSION.split("+")[0]
    print("  this file       : %s" % TOOL_VERSION)
    print("  +1 comment line : %s" % (drifted or "(unavailable)"))
    print("  version ends in its own sha256[:12] : %s"
          % ("yes" if anchored else "NO"))
    print("  one byte of drift moves the version : %s"
          % ("yes" if moved else "NO"))
    print("  series label unchanged by drift     : %s"
          % ("yes" if same_series else "NO"))
    ok = anchored and moved and same_series
    print("  -> %s" % ("PASS" if ok else "FAIL"))
    print()
    passes.append(ok)


def selftest():
    import tempfile
    print("=" * 70)
    print("ANTI-VACUITY SELFTEST")
    print("=" * 70)
    print()
    print("This tool exists to find suites that cannot fail. If it could only")
    print("return one verdict it would be that defect. Each fixture forces a")
    print("different answer on a case where the answer is known, and each")
    print("checks the source file is left byte-identical.")
    print()
    print("I1/I2 are a matched pair: the same fixture must read SURVIVED with")
    print("mutants traced and SURVIVED_OUT with mutants untraced. A control")
    print("that passes whatever the code does is a log line, so it is run in")
    print("both directions and the defect has to reappear on demand.")
    print()
    passes = []

    def fixture(name, mod_src, suite_src, expect, extra=None, trace=True):
        with tempfile.TemporaryDirectory() as d:
            mod = os.path.join(d, "target_module.py")
            open(mod, "w").write(mod_src)
            before = sha256(mod)
            open(os.path.join(d, "suite.py"), "w").write(suite_src)
            print("-" * 70)
            print("Fixture %s" % name)
            out = probe(mod, "%s suite.py" % sys.executable, d, 30, None, 0,
                        verbose=False, show_diff=False, trace_mutants=trace)
            if "abort" in out:
                got = "ABORT"
                print("  ABORT -- %s" % out["abort"].splitlines()[0])
            else:
                s = summarise(out, verbose=False)
                vs = [x["verdict"] for x in out["results"]]
                got = expect if expect in vs else sorted(set(vs))[0]
                print("  verdicts seen %s" % sorted(set(vs)))
                print("  killed=%d survivors=%d crashed=%d topology=%d "
                      "n=%d score=%s"
                      % (s["killed"], s["survivors"], s["crashed"],
                         s["topology"], s["n"],
                         "NO_MEASUREMENT" if s["score"] is None
                         else "%.1f%%" % s["score"]))
                if extra and not extra(s):
                    got = "%s+badcount" % got
            restored = sha256(mod) == before
            ok = (got == expect) and restored
            print("  expected %-13s got %-13s | restored %s  -> %s"
                  % (expect, got, "yes" if restored else "NO",
                     "PASS" if ok else "FAIL"))
            print()
            passes.append(ok)

    print("Fixture F is the coverage control: the suite exercises one")
    print("comparison and never calls the other. An instrument that cannot")
    print("tell them apart reports 50%% when the honest answer is 100%% of")
    print("what was actually measured, plus one site it never got to see.")
    print()

    fixture("A  suite genuinely constrains the module",
            MOD_PLAIN, S_CHECKS, "KILLED")
    fixture("B  suite prints 1000/1000, checks nothing",
            MOD_PLAIN, S_THEATRE, "SURVIVED")
    fixture("C  suite prints the broken value, still exits 0",
            MOD_PLAIN, S_NOISY, "SURVIVED_OUT")
    fixture("D  mutation breaks the module (must NOT count as a kill)",
            MOD_CRASHY, S_CRASHY, "CRASHED",
            extra=lambda s: s["crashed"] == 1 and s["killed"] == 0
            and s["n"] == 1)
    fixture("E  oracle already failing -- refuse to score",
            MOD_PLAIN, S_FAILING, "ABORT")
    fixture("F  one site exercised, one dormant (COVERAGE SABOTAGE CONTROL)",
            MOD_PARTIAL, S_PARTIAL, "KILLED",
            extra=lambda s: s["killed"] == 1 and s["unexercised"] == 1
            and s["n"] == 1)
    fixture("G  suite spawns an honest python child (TOPOLOGY: must attach)",
            MOD_PLAIN, S_MULTIPROC, "KILLED")
    fixture("H  suite spawns an env-stripped child (TOPOLOGY SABOTAGE: must "
            "fail closed)", MOD_PLAIN, S_SANITIZED, "ABORT")
    fixture("I1 mutants traced: tracer-sensitive suite must read SURVIVED "
            "(ENVIRONMENT PARITY CONTROL)",
            MOD_PLAIN, S_ENVPARITY, "SURVIVED",
            extra=lambda s: s["survived"] == 1 and s["survived_out"] == 0,
            trace=True)
    fixture("I2 same fixture, mutants UNtraced: the pre-v2.4 defect must "
            "reappear as SURVIVED_OUT (proves I1 can fail)",
            MOD_PLAIN, S_ENVPARITY, "SURVIVED_OUT",
            extra=lambda s: s["survived_out"] == 1, trace=False)
    fixture("J  mutation starts an unattachable child (PER-MUTANT TOPOLOGY "
            "CONTROL)", MOD_TOPOLOGY, S_CHECKS, "TOPOLOGY_CHANGED",
            extra=lambda s: s["topology"] == 1 and s["killed"] == 1
            and s["n"] == 1)

    fixture("L1 suite that refuses a second run (RE-RUNNABILITY SABOTAGE: "
            "must fail closed, not score every mutant KILLED)",
            MOD_PLAIN, S_ONESHOT, "ABORT")
    fixture("L2 same suite made idempotent: must still be measurable "
            "(proves L1 is not just refusing everything)",
            MOD_PLAIN, S_IDEMPOTENT, "KILLED")

    _abort_record_control(passes)
    _identity_control(passes)

    print("=" * 70)
    if all(passes):
        print("SELFTEST PASS %d/%d. The tool returns KILLED, SURVIVED,"
              % (len(passes), len(passes)))
        print("SURVIVED_OUT, CRASHED, NOT_EXERCISED, TOPOLOGY_CHANGED and")
        print("ABORT depending on input; excludes crashed, unexercised and")
        print("topology-changed sites from the score; runs mutants in the")
        print("same environment as the baseline, and reproduces the old")
        print("unlike-run confound on demand when that is switched off;")
        print("refuses to score when a python process ran unattached;")
        print("refuses to score a suite that will not run twice, because")
        print("every mutant after the first would be a false KILLED;")
        print("writes a machine-readable record when it aborts;")
        print("derives its declared version from its own bytes; and leaves")
        print("the source byte-identical.")
        print("=" * 70)
        return 0
    print("SELFTEST FAIL %d/%d. Do not trust any result from this run."
          % (sum(passes), len(passes)))
    print("=" * 70)
    return 1


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(
        description="Measure whether a test suite detects damage to the code "
                    "it tests.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", help=".py module to mutate (a WORKING COPY)")
    ap.add_argument("--suite", help="command that runs the suite; must exit 0")
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--sample", type=int, default=None,
                    help="mutate only K sites; K becomes the denominator")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--min-score", type=float, default=50.0)
    ap.add_argument("--verify-manifest", default=None,
                    help="SHA-256 manifest of the sealed tree; verified "
                         "before and after the run")
    ap.add_argument("--no-diff", action="store_true",
                    help="suppress per-mutant source diffs")
    ap.add_argument("--json", dest="json_out", default=None, metavar="PATH",
                    help="write the campaign as JSON (evidence only; no "
                         "interpretation of why a mutant survived)")
    ap.add_argument("--trace-baseline-only", action="store_true",
                    help="run mutants WITHOUT the coverage tracer. Faster, "
                         "but the baseline is then traced and the mutants are "
                         "not, so every verdict compares unlike runs. The "
                         "confound is recorded in the JSON rather than "
                         "assumed away. Default is off: mutants run traced.")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.source or not args.suite:
        ap.print_help()
        return 2

    try:
        out = probe(args.source, args.suite, os.path.abspath(args.cwd),
                    args.timeout, args.sample, args.seed,
                    manifest=args.verify_manifest, show_diff=not args.no_diff,
                    trace_mutants=not args.trace_baseline_only)
    except FileNotFoundError as e:
        sys.stderr.write("cannot look: no such file: %s\n" % e)
        return 2

    if "abort" in out:
        if args.json_out:
            import json
            camp = build_abort_campaign(out, args.source, args.suite,
                                        args.cwd, args.verify_manifest)
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(camp, f, indent=2, sort_keys=False)
            sys.stderr.write("abort record written to %s\n" % args.json_out)
        sys.stderr.write("cannot look: %s\n" % out["abort"])
        return 2

    if args.json_out:
        import json
        camp = build_campaign(out, args.verify_manifest)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(camp, f, indent=2, sort_keys=False)
        print("campaign JSON written to %s" % args.json_out)
        print()

    s = summarise(out)
    if s["n"] == 0:
        sys.stderr.write("cannot look: nothing resolved; every mutant was "
                         "excluded.\n")
        return 2
    return 0 if s["score"] >= args.min_score else 1


if __name__ == "__main__":
    sys.exit(main())

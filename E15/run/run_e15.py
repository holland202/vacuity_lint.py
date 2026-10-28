#!/usr/bin/env python3
"""E15 v2 run: scan the committed selection and evaluate P1-P4 as PREREG_v2.md registers.

Usage:
  python run_e15.py REPO_ROOT OUT_DIR WORK_DIR     # the real run
  python run_e15.py --selftest                     # no network, synthetic fixtures

REPO_ROOT is a checkout of vacuity_lint.py containing E15/selection/run/ and the
git history holding both pinned scanners. Each scanner is extracted from git and
checked by sha256 before the first scan; nothing else is ever used to scan.

Decisions fixed in this file BEFORE any scan (see E15/run/README.md):
  - A selected repository whose recorded commit can no longer be fetched is
    recorded as UNAVAILABLE, excluded from the analysis, and counted per arm.
  - P1 and P2 are directional difference claims. Each is CONFIRMED only if the
    medians differ in the predicted direction AND the registered Mann-Whitney
    test gives p < 0.05; otherwise NOT CONFIRMED. P3 and P4 use their own
    registered rules unchanged.
  - Bootstrap: resample each arm independently with replacement, 10,000 times,
    numpy.random.default_rng(20260908) created fresh for each interval.
  - P4: numpy.random.default_rng(20260908) created once; draws permutations of
    Arm C until 1000 distinct unordered half-splits exist.
  - Mann-Whitney: scipy.stats.mannwhitneyu, two-sided, default method.
  - A scanner traceback, or an exit code outside {0, 1, 2}, is an instrument
    defect: the run is VOIDED (freeze clause), not patched and continued.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np
from scipy import stats

PRIMARY = {"commit": "b0db5ac3fc2b20eb16abb6594f1e19746be62650",
           "blob": "14c728c316088ad41d86b1bac913d7dfead8077d",
           "sha256": "a92963c69fa129dbccf94e9672419c2dd2768950d97318183bc8b2820ee815d4"}
SECONDARY = {"commit": "e549dbfe9d8c0a03399bef45b66edf7bb6552f58",
             "path": "vacuity_lint.py",
             "sha256": "7a5b8d100457128f5cd17c418ea28af480e8c8a488968211508b08b09997292c"}
SEED = 20260908
N_BOOT = 10_000
N_SPLITS = 1000
ALPHA = 0.05
P3_MARGIN = 2.0
P4_BAND = (0.02, 0.08)
EXCLUDED_FILES = {"conftest.py"}
EXCLUDED_DIRS = {"examples", "example", ".venv", "site-packages", "node_modules", "third_party"}


class InstrumentDefect(Exception):
    pass


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def extract_instruments(repo_root, dest):
    os.makedirs(dest, exist_ok=True)
    prim = os.path.join(dest, "primary_vacuity_lint.py")
    sec = os.path.join(dest, "secondary_vacuity_lint.py")
    with open(prim, "wb") as f:
        f.write(subprocess.run(["git", "-C", repo_root, "cat-file", "-p", PRIMARY["blob"]],
                               capture_output=True, check=True).stdout)
    with open(sec, "wb") as f:
        f.write(subprocess.run(["git", "-C", repo_root, "show",
                                f"{SECONDARY['commit']}:{SECONDARY['path']}"],
                               capture_output=True, check=True).stdout)
    check_instruments(prim, sec)
    return prim, sec


def check_instruments(prim, sec):
    for path, want in ((prim, PRIMARY["sha256"]), (sec, SECONDARY["sha256"])):
        got = sha256(path)
        if got != want:
            raise InstrumentDefect(f"sha256 mismatch for {path}: {got} != {want}")


def fetch_tree(full_name, commit, dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")
    steps = [["git", "init", "-q", dest],
             ["git", "-C", dest, "fetch", "-q", "--depth", "1",
              f"https://github.com/{full_name}", commit],
             ["git", "-C", dest, "checkout", "-q", "FETCH_HEAD"]]
    for cmd in steps:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
        if p.returncode != 0:
            return False, p.stderr.strip()[-300:]
    got = subprocess.run(["git", "-C", dest, "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    if got != commit:
        return False, f"checked out {got}, expected {commit}"
    shutil.rmtree(os.path.join(dest, ".git"))
    return True, ""


def apply_exclusions(root):
    removed = {"files": 0, "dirs": 0, "py_files_removed": 0}
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        for d in list(dirnames):
            if d in EXCLUDED_DIRS:
                full = os.path.join(dirpath, d)
                removed["py_files_removed"] += sum(
                    1 for _, _, fs in os.walk(full) for fn in fs if fn.endswith(".py"))
                shutil.rmtree(full, ignore_errors=True)
                dirnames.remove(d)
                removed["dirs"] += 1
        for fn in filenames:
            if fn in EXCLUDED_FILES:
                os.remove(os.path.join(dirpath, fn))
                removed["files"] += 1
                removed["py_files_removed"] += fn.endswith(".py")
    return removed


def _run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if "Traceback (most recent call last)" in p.stderr or p.returncode not in (0, 1, 2):
        raise InstrumentDefect(f"{' '.join(cmd[-2:])}: exit {p.returncode}: {p.stderr.strip()[-400:]}")
    return p


def run_primary(prim, root):
    p = _run([sys.executable, "-I", prim, "--format", "json", root])
    d = json.loads(p.stdout)
    live = [f for f in d["findings"] if not f.get("suppressed")]
    return {"exit": p.returncode, "status": d["status"], "files_scanned": d["files_scanned"],
            "verification_shaped": d["verification_shaped"], "findings": len(live),
            "coverage_errors": len(d["coverage_errors"]),
            "rules": sorted({f["rule_id"] for f in live})}


SEC_RE = {k: re.compile(rf"^{re.escape(label)}\s*:\s*(\d+)\s*$", re.M) for k, label in
          (("files_scanned", "python files scanned"), ("verification_shaped", "verification-shaped"),
           ("findings", "findings"))}


def parse_secondary(text, exit_code):
    if exit_code == 2 and "nothing scanned" in text:
        return {"files_scanned": 0, "verification_shaped": 0, "findings": 0}
    out = {}
    for k, rx in SEC_RE.items():
        m = rx.findall(text)
        if len(m) != 1:
            return None
        out[k] = int(m[0])
    return out


def run_secondary(sec, root):
    p = _run([sys.executable, "-I", sec, root])
    parsed = parse_secondary(p.stdout + p.stderr, p.returncode)
    return None if parsed is None else {**parsed, "exit": p.returncode}


def bench_count(prim, root):
    n = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if fn.endswith(".py") and "bench" in os.path.relpath(full, root).lower():
                n += run_primary(prim, full)["verification_shaped"]
    return n


# ---------------------------------------------------------------- statistics

def mwu(x, y):
    return float(stats.mannwhitneyu(x, y, alternative="two-sided").pvalue)


def boot_median_diff(x, y):
    rng = np.random.default_rng(SEED)
    x, y = np.asarray(x, float), np.asarray(y, float)
    d = np.empty(N_BOOT)
    for i in range(N_BOOT):
        d[i] = np.median(rng.choice(x, x.size)) - np.median(rng.choice(y, y.size))
    lo, hi = np.percentile(d, [2.5, 97.5])
    return float(np.median(x) - np.median(y)), float(lo), float(hi)


def describe(v):
    v = np.asarray(v, float)
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    return {"n": int(v.size), "median": float(med), "q1": float(q1), "q3": float(q3),
            "values_sorted": sorted(int(x) for x in v)}


def directional(x, y, predicted_x_higher):
    p = mwu(x, y)
    diff, lo, hi = boot_median_diff(x, y)
    ok_dir = diff > 0 if predicted_x_higher else diff < 0
    return {"p": p, "median_diff": diff, "ci95": [lo, hi],
            "verdict": "CONFIRMED" if (p < ALPHA and ok_dir) else "NOT CONFIRMED"}


def p3(a, b):
    diff, lo, hi = boot_median_diff(a, b)
    if -P3_MARGIN <= lo and hi <= P3_MARGIN:
        v = "CONFIRMED"
    elif hi < -P3_MARGIN:
        v = "REFUTED"
    else:
        v = "INCONCLUSIVE"
    return {"median_diff": diff, "ci95": [lo, hi], "margin": P3_MARGIN, "verdict": v}


def p4(c):
    c = np.asarray(c, float)
    n = c.size
    half = n // 2
    import math
    if math.comb(n, half) // (2 if 2 * half == n else 1) < N_SPLITS:
        raise ValueError(f"only {math.comb(n, half)} splits exist for n={n}; cannot draw {N_SPLITS} distinct")
    rng = np.random.default_rng(SEED)
    seen, rates = set(), []
    while len(seen) < N_SPLITS:
        perm = rng.permutation(n)
        s = frozenset(perm[:half].tolist())
        key = min(s, frozenset(range(n)) - s, key=lambda z: sorted(z))
        if key in seen:
            continue
        seen.add(key)
        idx = np.array(sorted(s))
        rest = np.array(sorted(set(range(n)) - s))
        rates.append(mwu(c[idx], c[rest]) < ALPHA)
    prop = float(np.mean(rates))
    return {"splits": N_SPLITS, "evaluated": len(rates), "half_size": half,
            "proportion_p_below_alpha": prop,
            "band": list(P4_BAND),
            "verdict": "PASS" if P4_BAND[0] <= prop <= P4_BAND[1] else "FAIL"}


def clopper_pearson(k, n):
    ci = stats.binomtest(k, n).proportion_ci(confidence_level=0.95, method="exact")
    return [float(ci.low), float(ci.high)]


def analyse(records, field="verification_shaped", instrument="primary"):
    arms = {a: [r[instrument][field] for r in records
                if r["arm"] == a and r.get(instrument) is not None] for a in "ABC"}
    res = {"per_arm": {a: describe(v) for a, v in arms.items()}}
    res["P1_C_gt_B"] = directional(arms["C"], arms["B"], True)
    res["P2_A_lt_C"] = directional(arms["A"], arms["C"], False)
    res["P3_A_equiv_B"] = p3(arms["A"], arms["B"])
    res["P4_control"] = p4(arms["C"])
    if res["P4_control"]["verdict"] == "FAIL":
        res["note"] = "P4 FAILED: all between-arm comparisons are void (PREREG_v2)."
    return res


# ---------------------------------------------------------------- run

def load_selection(repo_root):
    base = os.path.join(repo_root, "E15", "selection", "run")
    pool = json.load(open(os.path.join(base, "selection.json")))
    arm_a = json.load(open(os.path.join(base, "arm_a.json")))
    return [r for r in arm_a + pool if r.get("eligible")]


def main_run(repo_root, out_dir, work_dir):
    os.makedirs(out_dir, exist_ok=True)
    prim, sec = extract_instruments(repo_root, os.path.join(work_dir, "instruments"))
    selected = load_selection(repo_root)
    records, sec_ok = [], True
    log = open(os.path.join(out_dir, "scan_progress.jsonl"), "w")
    try:
        for i, s in enumerate(selected, 1):
            check_instruments(prim, sec)
            dest = os.path.join(work_dir, "trees", s["full_name"].replace("/", "__"))
            rec = {"full_name": s["full_name"], "arm": s["arm"], "commit": s["commit"]}
            ok, err = fetch_tree(s["full_name"], s["commit"], dest)
            if not ok:
                rec.update(available=False, fetch_error=err)
            else:
                rec["available"] = True
                rec["excluded"] = apply_exclusions(dest)
                rec["primary"] = run_primary(prim, dest)
                rec["secondary"] = run_secondary(sec, dest)
                sec_ok &= rec["secondary"] is not None
                rec["bench_verification_shaped"] = bench_count(prim, dest)
            records.append(rec)
            log.write(json.dumps(rec) + "\n")
            log.flush()
            print(f"[{i:3d}/{len(selected)}] arm {rec['arm']} "
                  f"{'ok' if rec['available'] else 'UNAVAILABLE'}", flush=True)
        check_instruments(prim, sec)
    except InstrumentDefect as e:
        json.dump({"status": "VOID", "reason": str(e), "scanned_before_void": len(records)},
                  open(os.path.join(out_dir, "results.json"), "w"), indent=1)
        print(f"VOID: {e}")
        return 3
    finally:
        log.close()
    avail = [r for r in records if r["available"]]
    results = {
        "status": "COMPLETE",
        "instruments": {"primary": PRIMARY, "secondary": SECONDARY},
        "unavailable_per_arm": {a: sum(1 for r in records if r["arm"] == a and not r["available"])
                                for a in "ABC"},
        "primary": analyse(avail),
        "secondary_outcome_any_finding": {
            a: (lambda k, n: {"k": k, "n": n, "proportion": k / n if n else None,
                              "ci95": clopper_pearson(k, n) if n else None})(
                sum(1 for r in avail if r["arm"] == a and r["primary"]["findings"] > 0),
                sum(1 for r in avail if r["arm"] == a)) for a in "ABC"},
        "coverage_error_repos_per_arm": {a: sum(1 for r in avail if r["arm"] == a
                                                and r["primary"]["coverage_errors"])
                                         for a in "ABC"},
        "bench_verification_shaped_per_arm": {a: sum(r["bench_verification_shaped"] for r in avail
                                                     if r["arm"] == a) for a in "ABC"},
        "sensitivity_secondary_instrument": (analyse(avail, instrument="secondary")
                                             if sec_ok else "NOT RUN: parser failed on at least one repository"),
    }
    json.dump(records, open(os.path.join(out_dir, "scans.json"), "w"), indent=1)
    json.dump(results, open(os.path.join(out_dir, "results.json"), "w"), indent=1)
    r = results["primary"]
    print(json.dumps({k: r[k]["verdict"] for k in ("P1_C_gt_B", "P2_A_lt_C", "P3_A_equiv_B", "P4_control")}))
    return 0


# ---------------------------------------------------------------- selftest

def selftest():
    import tempfile
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {msg}")

    with tempfile.TemporaryDirectory() as d:
        for rel in ["a/conftest.py", "a/keep.py", "examples/x.py", "pkg/example/y.py",
                    "pkg/third_party/z.py", "node_modules/n.py", "pkg/examples_not/k.py"]:
            os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
            open(os.path.join(d, rel), "w").close()
        r = apply_exclusions(d)
        left = sorted(os.path.relpath(os.path.join(dp, f), d) for dp, _, fs in os.walk(d) for f in fs)
        check(left == ["a/keep.py", "pkg/examples_not/k.py"] and r["py_files_removed"] == 5,
              f"exclusions remove exactly the registered paths -> kept {left}, removed {r}")
    text = "python files scanned    : 7\nverification-shaped     : 3\nfindings                : 1\n"
    check(parse_secondary(text, 1) == {"files_scanned": 7, "verification_shaped": 3, "findings": 1},
          "secondary parser reads the three counts")
    check(parse_secondary("garbage", 0) is None and parse_secondary(text + text, 1) is None,
          "secondary parser refuses unparseable or ambiguous (repeated) output")
    check(parse_secondary("nothing scanned - no python files found under: x", 2)
          == {"files_scanned": 0, "verification_shaped": 0, "findings": 0},
          "secondary parser maps the empty-scan message to zeros")
    with tempfile.TemporaryDirectory() as d:
        fake = os.path.join(d, "s.py")
        open(fake, "w").write("x")
        try:
            check_instruments(fake, fake)
            ok = False
        except InstrumentDefect:
            ok = True
        check(ok, "instrument check rejects a file whose sha256 does not match")
        bad = os.path.join(d, "boom.py")
        open(bad, "w").write("raise RuntimeError('x')\n")
        try:
            _run([sys.executable, bad, d])
            ok = False
        except InstrumentDefect:
            ok = True
        check(ok, "a scanner traceback is treated as an instrument defect")
    rng = np.random.default_rng(1)
    same = rng.poisson(5, 20)
    r4 = p4(same)
    check(0.0 <= r4["proportion_p_below_alpha"] <= 0.15 and r4["evaluated"] == N_SPLITS,
          f"P4 on one distribution: {r4['splits']} distinct splits, rate {r4['proportion_p_below_alpha']:.3f}")
    lo_x, hi_x = rng.poisson(2, 20), rng.poisson(30, 20)
    d1 = directional(hi_x, lo_x, True)
    d2 = directional(lo_x, lo_x + 0, True)
    d3 = directional(lo_x, hi_x, True)
    check(d1["verdict"] == "CONFIRMED" and d2["verdict"] == "NOT CONFIRMED" and d3["verdict"] == "NOT CONFIRMED",
          f"directional test: large shift CONFIRMED (p={d1['p']:.2g}), null and wrong direction NOT CONFIRMED")
    r3a = p3(np.full(20, 5), np.full(20, 5))
    r3b = p3(np.full(20, 1), np.full(20, 30))
    r3c = p3(np.r_[np.full(10, 1), np.full(10, 6)], np.full(20, 5))
    check(r3a["verdict"] == "CONFIRMED" and r3b["verdict"] == "REFUTED" and r3c["verdict"] == "INCONCLUSIVE",
          f"P3 rules: equal -> {r3a['verdict']}, far below -> {r3b['verdict']}, mixed -> {r3c['verdict']}")
    ci = clopper_pearson(0, 20)
    check(ci[0] == 0.0 and 0.16 < ci[1] < 0.17, f"Clopper-Pearson 0/20 -> {ci}")
    total = 10
    print(f"{total - fails}/{total} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(selftest())
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    sys.exit(main_run(*sys.argv[1:]))

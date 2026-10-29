#!/usr/bin/env python3
"""E15-B run: scan the author's repositories at their 2026-07-27 commits and evaluate the
classification, P1 and P2 exactly as E15B/PREREG.md registers them.

Usage:
  python E15B/run/run_e15b.py run REPO_ROOT OUT_DIR WORK_DIR   # the real run (network)
  python E15B/run/run_e15b.py evaluate OUT_DIR                 # rescore OUT_DIR/scans.json offline
  python E15B/run/run_e15b.py --selftest                       # no network

REPO_ROOT is a checkout of vacuity_lint.py with E15/ and the history holding both pinned
scanners. Imported, not copied: E15/run/run_e15.py (instrument extraction and sha256 checks,
fetch_tree, apply_exclusions, run_primary, run_secondary, InstrumentDefect) and
E15/selection/select_e15.py (count_py, failed_rule). Decisions PREREG.md leaves open are fixed
in E15B/run/README.md, committed with this file before any scan.

Until RECORDED is pinned (a separate commit after the run), `evaluate` exits 0. Once pinned, it
exits 0 only when (classification, P1, P2, digest) equal RECORDED.
"""
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

CUTOFF = "2026-07-27T23:59:59Z"
CUTOFF_EPOCH = int(dt.datetime(2026, 7, 27, 23, 59, 59, tzinfo=dt.timezone.utc).timestamp())
REPRODUCES_MAX = 2.4
DOES_NOT_REPRODUCE_MIN = 4.8
ALPHA = 0.05
RECORDED = ("DOES NOT REPRODUCE", "REFUTED", "NOT CONFIRMED",
            "4ecac6843cd1263d38e9eee308550fa2a57bc90bc4b55bfe14bb485a24f45d77")  # pinned after the 2026-10-29 run


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


E = load("run_e15", os.path.join(ROOT, "E15", "run", "run_e15.py"))
S = load("select_e15", os.path.join(ROOT, "E15", "selection", "select_e15.py"))

GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")


def git(args, cwd=None, timeout=600):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          env=GIT_ENV, timeout=timeout)


# ---------------------------------------------------------------- July commit

def g1_holds(july_ct, child_ct):
    """G1: the July commit is at or before the cutoff and its first-parent child is after it."""
    return july_ct <= CUTOFF_EPOCH and (child_ct is None or child_ct > CUTOFF_EPOCH)


def resolve_july(url, dest):
    """Clone the default branch's history and find the newest first-parent commit with a
    committer date at or before CUTOFF. G1 is checked here: that commit's date is at or before
    the cutoff, and its first-parent child, if any, is after it."""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    args = ["clone", "-q", "--no-checkout"] + (["--filter=blob:none"] if url.startswith("https://") else [])
    p = git(args + [url, dest])
    if p.returncode != 0:
        return {"ok": False, "error": p.stderr.strip()[-300:]}
    try:
        branch = git(["-C", dest, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        july = git(["-C", dest, "rev-list", "-1", "--first-parent", f"--before={CUTOFF}", "HEAD"]).stdout.strip()
        out = {"ok": True, "default_branch": branch, "july_commit": july or None}
        if not july:
            return out
        chain = [ln.split() for ln in git(["-C", dest, "log", "--first-parent", "--format=%H %ct", "HEAD"])
                 .stdout.strip().splitlines()]
        idx = [sha for sha, _ in chain].index(july)
        july_ct = int(chain[idx][1])
        child = chain[idx - 1] if idx > 0 else None
        out.update(july_committer_epoch=july_ct,
                   child_commit=child[0] if child else None,
                   child_committer_epoch=int(child[1]) if child else None)
        out["g1"] = g1_holds(july_ct, int(child[1]) if child else None)
        return out
    finally:
        shutil.rmtree(dest, ignore_errors=True)


# ---------------------------------------------------------------- population

def population(repo_root):
    """E15 v2's committed Arm A listing, forks excluded; each with its E15 commit and count."""
    base = os.path.join(repo_root, "E15")
    listing = json.load(open(os.path.join(base, "selection", "run", "arm_a.json")))
    scans = {r["full_name"]: r for r in json.load(open(os.path.join(base, "run", "output", "scans.json")))
             if r["arm"] == "A" and r.get("available")}
    pop, forks = [], []
    for r in sorted(listing, key=lambda x: x["full_name"]):
        if r.get("fork"):
            forks.append(r["full_name"])
            continue
        s = scans.get(r["full_name"])
        pop.append({"full_name": r["full_name"], "owner": r["owner"],
                    "e15_commit": s["commit"] if s else None,
                    "e15_count": s["primary"]["verification_shaped"] if s else None})
    return pop, forks


# ---------------------------------------------------------------- analysis

def classify(m):
    if m is None:
        return "NO DATA"
    if m <= REPRODUCES_MAX:
        return "REPRODUCES"
    if m >= DOES_NOT_REPRODUCE_MIN:
        return "DOES NOT REPRODUCE"
    return "INCONCLUSIVE"


def sign_test(pairs):
    from scipy import stats
    inc = sum(1 for e15, july in pairs if e15 > july)
    dec = sum(1 for e15, july in pairs if e15 < july)
    ties = len(pairs) - inc - dec
    p = float(stats.binomtest(inc, inc + dec, 0.5, alternative="two-sided").pvalue) if inc + dec else None
    ok = inc > dec and p is not None and p < ALPHA
    return {"increases": inc, "decreases": dec, "ties": ties, "p": p,
            "verdict": "CONFIRMED" if ok else "NOT CONFIRMED"}


def digest_of(records, verdicts):
    rows = sorted([r["full_name"], r.get("july_commit"), r.get("eligible_july"),
                   (r.get("primary") or {}).get("verification_shaped"), r.get("e15_count")] for r in records)
    canon = json.dumps({"rows": rows, "verdicts": verdicts}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def analyse(records):
    gate_failures = [f"G1 {r['full_name']}" for r in records if r.get("g1") is False]
    gate_failures += [f"G0 {r['full_name']}: {r['g0']}" for r in records
                      if r.get("g0") not in (None, "match")]
    arm_j = [r for r in records if r.get("eligible_july") and r.get("primary")]
    values = [r["primary"]["verification_shaped"] for r in arm_j]
    mean = sum(values) / len(values) if values else None
    srt = sorted(values)
    median = None
    if srt:
        mid = len(srt) // 2
        median = srt[mid] if len(srt) % 2 else (srt[mid - 1] + srt[mid]) / 2
    cls = classify(mean)
    p1 = "NO DATA" if mean is None else ("HELD" if cls == "REPRODUCES" else "REFUTED")
    pairs = [(r["e15_count"], r["primary"]["verification_shaped"]) for r in arm_j if r.get("e15_count") is not None]
    p2 = sign_test(pairs)
    status = "VOID" if gate_failures else "COMPLETE"
    verdicts = {"status": status, "classification": cls, "P1": p1, "P2": p2["verdict"]}
    sec = [r for r in arm_j if r.get("secondary")]
    return {
        "status": status, "gate_failures": gate_failures,
        "arm_j": {"n": len(values), "mean": mean, "median": median, "values_sorted": srt,
                  "py_files_scanned": sum(r["primary"]["files_scanned"] for r in arm_j)},
        "classification": cls, "P1": p1, "P2": p2,
        "counts": {k: sum(1 for r in records if r.get("state") == k)
                   for k in ("SCANNED", "INELIGIBLE AT JULY COMMIT", "NO JULY COMMIT", "UNAVAILABLE")},
        "secondary_per_repo_diff": {r["full_name"]: r["primary"]["verification_shaped"]
                                    - r["secondary"]["verification_shaped"] for r in sec},
        "digest": digest_of(records, verdicts),
        "verdicts": verdicts,
    }


def report(res):
    j = res["arm_j"]
    mean = "n/a" if j["mean"] is None else f"{j['mean']:.4f}"
    lines = [f"STATUS {res['status']}" + (f" ({'; '.join(res['gate_failures'])})" if res["gate_failures"] else ""),
             f"ARM J n={j['n']} mean={mean} median={j['median']} values={j['values_sorted']}",
             f"CLASSIFICATION {res['classification']} (REPRODUCES <= {REPRODUCES_MAX}, "
             f"DOES NOT REPRODUCE >= {DOES_NOT_REPRODUCE_MIN})",
             f"P1 {res['P1']}: registered REPRODUCES",
             f"P2 {res['P2']['verdict']}: increases {res['P2']['increases']}, decreases {res['P2']['decreases']}, "
             f"ties {res['P2']['ties']}, sign-test p={res['P2']['p']}",
             f"DIGEST {res['digest']}"]
    return lines


def finish(res):
    for line in report(res):
        print(line)
    if RECORDED is None:
        print("RECORDED not pinned yet: exit 0")
        return 0
    key = (res["classification"], res["P1"], res["P2"]["verdict"], res["digest"])
    same = key == tuple(RECORDED)
    print(f"{'matches' if same else 'DIFFERS FROM'} RECORDED")
    return 0 if same else 1


# ---------------------------------------------------------------- run

def scan(prim, sec, full_name, commit, dest):
    ok, err = E.fetch_tree(full_name, commit, dest)
    if not ok:
        ok, err = E.fetch_tree(full_name, commit, dest)  # one retry, README decision 5
    if not ok:
        return None, err
    n_py = S.count_py(dest)
    rec = {"py_files": n_py, "failed_rule": S.failed_rule(n_py, "holland202", check_owner=False)}
    if rec["failed_rule"] is None:
        rec["excluded"] = E.apply_exclusions(dest)
        rec["primary"] = E.run_primary(prim, dest)
        rec["secondary"] = E.run_secondary(sec, dest)
    shutil.rmtree(dest, ignore_errors=True)
    return rec, ""


def main_run(repo_root, out_dir, work_dir):
    os.makedirs(out_dir, exist_ok=True)
    prim, sec = E.extract_instruments(repo_root, os.path.join(work_dir, "instruments"))
    pop, forks = population(repo_root)
    records = []
    log = open(os.path.join(out_dir, "scan_progress.jsonl"), "w")
    try:
        for i, p in enumerate(pop, 1):
            E.check_instruments(prim, sec)
            rec = dict(p)
            jr = resolve_july(f"https://github.com/{p['full_name']}",
                              os.path.join(work_dir, "history", p["full_name"].replace("/", "__")))
            rec.update({k: v for k, v in jr.items() if k != "ok"})
            if not jr["ok"]:
                rec["state"] = "UNAVAILABLE"
            elif jr["july_commit"] is None:
                rec["state"] = "NO JULY COMMIT"
            else:
                dest = os.path.join(work_dir, "trees", p["full_name"].replace("/", "__"))
                s, err = scan(prim, sec, p["full_name"], jr["july_commit"], dest)
                if s is None:
                    rec.update(state="UNAVAILABLE", fetch_error=err)
                else:
                    rec.update(s)
                    rec["eligible_july"] = s["failed_rule"] is None
                    rec["state"] = "SCANNED" if rec["eligible_july"] else "INELIGIBLE AT JULY COMMIT"
                    if rec["eligible_july"] and p["e15_commit"]:
                        g, err = scan(prim, sec, p["full_name"], p["e15_commit"], dest + "__e15")
                        got = None if g is None or not g.get("primary") else g["primary"]["verification_shaped"]
                        rec["g0_count"] = got
                        rec["g0"] = "match" if got == p["e15_count"] else (
                            f"could not check ({err})" if g is None else f"mismatch: {got} != {p['e15_count']}")
            records.append(rec)
            log.write(json.dumps(rec) + "\n")
            log.flush()
            jc = (rec.get("july_commit") or "-")[:7]
            vs = (rec.get("primary") or {}).get("verification_shaped")
            print(f"[{i:2d}/{len(pop)}] {p['full_name']:45s} {rec['state']:26s} july {jc} "
                  f"vs={vs} e15={p['e15_count']} g1={rec.get('g1')} g0={rec.get('g0')}", flush=True)
        E.check_instruments(prim, sec)
    except E.InstrumentDefect as e:
        json.dump({"status": "VOID", "reason": str(e), "scanned_before_void": len(records)},
                  open(os.path.join(out_dir, "results.json"), "w"), indent=1)
        print(f"VOID: {e}")
        return 3
    finally:
        log.close()
    res = analyse(records)
    res.update(cutoff=CUTOFF, forks_excluded=forks,
               instruments={"primary": E.PRIMARY, "secondary": E.SECONDARY})
    json.dump(records, open(os.path.join(out_dir, "scans.json"), "w"), indent=1)
    json.dump(res, open(os.path.join(out_dir, "results.json"), "w"), indent=1)
    return finish(res)


def main_evaluate(out_dir):
    records = json.load(open(os.path.join(out_dir, "scans.json")))
    return finish(analyse(records))


# ---------------------------------------------------------------- selftest

def _commit(repo, name, iso):
    env = dict(GIT_ENV, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
               GIT_AUTHOR_DATE=iso, GIT_COMMITTER_DATE=iso)
    open(os.path.join(repo, name), "w").write(name)
    subprocess.run(["git", "-C", repo, "add", name], check=True, env=env)
    subprocess.run(["git", "-C", repo, "commit", "-q", "-m", name], check=True, env=env)
    return subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def _rec(name, july, e15, g1=True, g0="match", eligible=True):
    return {"full_name": name, "july_commit": "x" + name, "g1": g1, "g0": g0, "eligible_july": eligible,
            "state": "SCANNED", "e15_count": e15,
            "primary": {"verification_shaped": july, "files_scanned": 10},
            "secondary": {"verification_shaped": july}}


def selftest():
    checks = []

    def check(ok, what):
        checks.append(bool(ok))
        print(f"[{'PASS' if ok else 'FAIL'}] {what}")

    check([classify(x) for x in (2.4, 2.41, 4.79, 4.8, None)] ==
          ["REPRODUCES", "INCONCLUSIVE", "INCONCLUSIVE", "DOES NOT REPRODUCE", "NO DATA"],
          "classification bands and their edges")
    c = CUTOFF_EPOCH
    check([g1_holds(c, None), g1_holds(c + 1, None), g1_holds(c - 5, c), g1_holds(c - 5, c + 1)] ==
          [True, False, False, True], "G1 predicate in both directions")
    st = sign_test([(5, 1)] * 9 + [(1, 5)])
    check(st["verdict"] == "CONFIRMED" and abs(st["p"] - 0.021484375) < 1e-12, "sign test: 9 up, 1 down confirms")
    check(sign_test([(5, 1)] * 7 + [(1, 5)] * 3)["verdict"] == "NOT CONFIRMED", "sign test: 7 up, 3 down does not")
    check(sign_test([(1, 5)] * 9 + [(5, 1)])["verdict"] == "NOT CONFIRMED", "sign test: the wrong direction does not")
    st = sign_test([(3, 3)] * 4 + [(5, 1)] * 9 + [(1, 5)])
    check(st["ties"] == 4 and st["verdict"] == "CONFIRMED", "sign test: ties are dropped")
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "src")
        os.makedirs(src)
        subprocess.run(["git", "init", "-q", "-b", "main", src], check=True)
        _commit(src, "a", "2026-07-01T00:00:00Z")
        c2 = _commit(src, "b", "2026-07-27T23:00:00Z")
        c3 = _commit(src, "c", "2026-07-28T01:00:00Z")
        r = resolve_july(src, os.path.join(tmp, "clone"))
        check(r["july_commit"] == c2 and r["child_commit"] == c3 and r["g1"] is True,
              "July commit is the last one at or before the cutoff; G1 holds")
        late = os.path.join(tmp, "late")
        os.makedirs(late)
        subprocess.run(["git", "init", "-q", "-b", "main", late], check=True)
        _commit(late, "a", "2026-08-01T00:00:00Z")
        check(resolve_july(late, os.path.join(tmp, "clone2"))["july_commit"] is None,
              "a repository created after the cutoff has no July commit")
        check(resolve_july(os.path.join(tmp, "missing"), os.path.join(tmp, "clone3"))["ok"] is False,
              "a clone failure is reported, not raised")
    base = [_rec(f"r{i}", 1, 10) for i in range(9)] + [_rec("r9", 3, 2)]
    res = analyse(base)
    check(res["status"] == "COMPLETE" and res["classification"] == "REPRODUCES" and res["P1"] == "HELD"
          and res["P2"]["verdict"] == "CONFIRMED", "a clean synthetic run scores as registered")
    check(analyse(base[:-1] + [_rec("r9", 3, 2, g0="mismatch: 4 != 2")])["status"] == "VOID",
          "a G0 mismatch voids the run")
    check(analyse(base[:-1] + [_rec("r9", 3, 2, g0="could not check (x)")])["status"] == "VOID",
          "a G0 check that could not run voids the run")
    check(analyse(base[:-1] + [_rec("r9", 3, 2, g1=False)])["status"] == "VOID", "a G1 failure voids the run")
    check(analyse([_rec(f"r{i}", 6, 10) for i in range(5)])["classification"] == "DOES NOT REPRODUCE",
          "high July counts classify as DOES NOT REPRODUCE")
    check(analyse(base + [_rec("rx", 50, 1, eligible=False)])["arm_j"]["n"] == 10,
          "a repository ineligible at its July commit is not in Arm J")
    check(analyse(list(reversed(base)))["digest"] == res["digest"], "the digest does not depend on record order")
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "E15", "selection", "run"))
        os.makedirs(os.path.join(tmp, "E15", "run", "output"))
        json.dump([{"full_name": "o/b", "owner": "o", "fork": False}, {"full_name": "o/a", "owner": "o", "fork": True}],
                  open(os.path.join(tmp, "E15", "selection", "run", "arm_a.json"), "w"))
        json.dump([{"full_name": "o/b", "arm": "A", "available": True, "commit": "c",
                    "primary": {"verification_shaped": 7}}],
                  open(os.path.join(tmp, "E15", "run", "output", "scans.json"), "w"))
        pop, forks = population(tmp)
        check(forks == ["o/a"] and pop == [{"full_name": "o/b", "owner": "o", "e15_commit": "c", "e15_count": 7}],
              "forks are excluded and listed; E15 commit and count attach")
    n = sum(checks)
    print(f"{n}/{len(checks)} checks passed")
    return 0 if n == len(checks) else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--selftest"]:
        sys.exit(selftest())
    if len(a) == 2 and a[0] == "evaluate":
        sys.exit(main_evaluate(os.path.abspath(a[1])))
    if len(a) == 4 and a[0] == "run":
        sys.exit(main_run(*[os.path.abspath(x) for x in a[1:]]))
    print(__doc__)
    sys.exit(2)

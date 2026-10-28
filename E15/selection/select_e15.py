#!/usr/bin/env python3
"""E15 v2 selection: draw the sample exactly as PREREG_v2.md registers it.

This script SELECTS. It never runs vacuity_lint or any other scanner.

What it does, in order:
  1. Queries the GitHub search API with the registered pool query, sorted by
     stars descending, 100 per page, fetching a page only when the previous
     one is used up. Every raw response (headers + body) is saved with its
     retrieval timestamp under raw/ before any item from it is processed.
  2. Takes repositories in returned order. For each: depth-1 clone with a
     120 s limit, count *.py files, apply eligibility rules 1-4, stratify
     eligible ones into Arm B / Arm C by the registered CI config paths.
  3. Stops when BOTH Arm B and Arm C have at least 20 repositories, or when
     200 eligible repositories have been taken (shortfall), or when the
     search results run out (shortfall).
  4. Builds Arm A: every public repository owned by holland202, rules 1-3.
  5. Writes selection.json, selection.csv, arm_a.json and run_meta.json.

Usage:  python3 select_e15.py OUT_DIR CLONE_DIR
        python3 select_e15.py --selftest
"""
import csv
import datetime as dt
import fnmatch
import json
import os
import platform
import shutil
import subprocess
import sys
import time

QUERY = "language:Python stars:5..50 pushed:>2025-09-08 fork:false archived:false"
PER_PAGE = 100
TARGET = 20
MAX_ELIGIBLE = 200
CLONE_TIMEOUT_S = 120
QUIET = False
OWNER_EXCLUDED = "holland202"
CI_PATTERNS = [
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".travis.yml",
    ".circleci/config.yml",
    "azure-pipelines.yml",
]


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def gh_get(path, params, raw_path):
    """GET via `gh api --include`; save headers+body verbatim; return parsed body."""
    cmd = ["gh", "api", "-X", "GET", "--include", path]
    for k, v in params.items():
        cmd += ["-f", f"{k}={v}"]
    ts = utcnow()
    p = subprocess.run(cmd, capture_output=True, text=True)
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(f"# retrieved_utc: {ts}\n# command: {' '.join(cmd)}\n# exit: {p.returncode}\n")
        f.write(p.stdout)
        if p.stderr:
            f.write("\n# stderr:\n" + p.stderr)
    if p.returncode != 0:
        raise RuntimeError(f"gh api failed ({p.returncode}) for {path}; raw saved to {raw_path}")
    body = p.stdout.split("\r\n\r\n", 1)[-1] if "\r\n\r\n" in p.stdout else p.stdout.split("\n\n", 1)[-1]
    return json.loads(body), ts


def has_ci(root):
    hits = []
    for pat in CI_PATTERNS:
        d, base = os.path.split(pat)
        full_d = os.path.join(root, d) if d else root
        if not os.path.isdir(full_d):
            continue
        for name in sorted(os.listdir(full_d)):
            if fnmatch.fnmatchcase(name, base) and os.path.isfile(os.path.join(full_d, name)):
                hits.append(os.path.join(d, name) if d else name)
    return hits


def count_py(root):
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirnames:
            dirnames.remove(".git")
        n += sum(1 for fn in filenames if fn.endswith(".py") and os.path.isfile(os.path.join(dirpath, fn)))
    return n


def clone(full_name, clone_dir):
    dest = os.path.join(clone_dir, full_name.replace("/", "__"))
    if os.path.exists(dest):
        shutil.rmtree(dest)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")
    t0 = time.monotonic()
    try:
        p = subprocess.run(
            ["git", "clone", "-q", "--depth", "1", f"https://github.com/{full_name}", dest],
            capture_output=True, text=True, timeout=CLONE_TIMEOUT_S, env=env)
        ok, err = p.returncode == 0, p.stderr.strip()[-500:]
    except subprocess.TimeoutExpired:
        ok, err = False, f"timeout after {CLONE_TIMEOUT_S}s"
    secs = round(time.monotonic() - t0, 2)
    sha = None
    if ok:
        sha = subprocess.run(["git", "-C", dest, "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
    return ok, err, secs, sha, dest


def evaluate(full_name, owner, clone_dir, check_owner=True):
    """Apply eligibility in registered order. Rules 1-2 need the clone, so a
    clone failure is recorded as an eligibility-3 failure (as PREREG says)."""
    rec = {"full_name": full_name, "owner": owner, "evaluated_utc": utcnow()}
    ok, err, secs, sha, dest = clone(full_name, clone_dir)
    rec.update(clone_ok=ok, clone_seconds=secs, commit=sha)
    if not ok:
        rec.update(eligible=False, failed_rule=3, clone_error=err)
        return rec, None
    n = count_py(dest)
    rule = failed_rule(n, owner, check_owner)
    rec.update(py_files=n, eligible=rule is None, failed_rule=rule)
    return rec, dest


def failed_rule(n_py, owner, check_owner=True):
    """First registered eligibility rule (1, 2 or 4) that fails, or None.
    Rule 3 (clone) is decided before this is called."""
    if n_py < 5:
        return 1
    if n_py > 2000:
        return 2
    if check_owner and owner.lower() == OWNER_EXCLUDED:
        return 4
    return None


def log_line(path, rec):
    """Append one record as it is decided, so an interrupted run leaves a trace."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def select_pool(out_dir, clone_dir):
    raw_dir = os.path.join(out_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    progress = os.path.join(out_dir, "progress.jsonl")
    records, seen, page = [], set(), 0
    arms = {"B": 0, "C": 0}
    eligible = 0
    stop_reason, total_count = None, None
    while stop_reason is None:
        page += 1
        params = {"q": QUERY, "sort": "stars", "order": "desc",
                  "per_page": str(PER_PAGE), "page": str(page)}
        try:
            body, ts = gh_get("search/repositories", params,
                              os.path.join(raw_dir, f"search_page_{page:03d}.txt"))
        except RuntimeError as e:
            stop_reason = f"search API error on page {page}: {e}"
            break
        total_count = body.get("total_count", total_count)
        items = body.get("items", [])
        if not items:
            stop_reason = f"search results exhausted at page {page}"
            break
        for pos, it in enumerate(items, 1):
            full_name = it["full_name"]
            base = {"order": len(records) + 1, "page": page, "page_position": pos,
                    "page_retrieved_utc": ts, "stars": it.get("stargazers_count")}
            if full_name.lower() in seen:
                records.append({**base, "full_name": full_name, "eligible": False,
                                "failed_rule": None, "duplicate_in_results": True})
                log_line(progress, records[-1])
                continue
            seen.add(full_name.lower())
            rec, dest = evaluate(full_name, it["owner"]["login"], clone_dir)
            rec = {**base, **rec}
            if rec["eligible"]:
                eligible += 1
                ci = has_ci(dest)
                rec["ci_paths"] = ci
                rec["arm"] = "C" if ci else "B"
                arms[rec["arm"]] += 1
            records.append(rec)
            log_line(progress, rec)
            if not QUIET:
                print(f"[{rec['order']:4d}] eligible={eligible:3d} B={arms['B']:2d} C={arms['C']:2d}", flush=True)
            if arms["B"] >= TARGET and arms["C"] >= TARGET:
                stop_reason = "both strata reached 20"
                break
            if eligible >= MAX_ELIGIBLE:
                stop_reason = "shortfall: 200 eligible repositories taken without both strata reaching 20"
                break
    return records, arms, eligible, stop_reason, total_count, page


def select_arm_a(out_dir, clone_dir):
    raw_dir = os.path.join(out_dir, "raw")
    repos, page = [], 0
    while True:
        page += 1
        body, ts = gh_get(f"users/{OWNER_EXCLUDED}/repos",
                          {"type": "owner", "per_page": "100", "page": str(page), "sort": "full_name"},
                          os.path.join(raw_dir, f"arm_a_page_{page:03d}.txt"))
        if not body:
            break
        repos += [(r, ts) for r in body]
    out = []
    for r, ts in repos:
        if r.get("private"):
            continue
        rec, _ = evaluate(r["full_name"], r["owner"]["login"], clone_dir, check_owner=False)
        rec.update(fork=r.get("fork"), archived=r.get("archived"), listing_retrieved_utc=ts)
        if rec["eligible"]:
            rec["arm"] = "A"
        out.append(rec)
        log_line(os.path.join(out_dir, "progress.jsonl"), rec)
    return out


def selftest():
    import tempfile
    global QUIET
    QUIET = True
    fails = 0
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, ".github", "workflows"))
        open(os.path.join(d, ".github", "workflows", "ci.yml"), "w").close()
        open(os.path.join(d, ".github", "workflows", "notes.txt"), "w").close()
        got = has_ci(d)
        fails += got != [".github/workflows/ci.yml"]
        print("[%s] has_ci finds .yml, ignores .txt -> %s" % ("PASS" if got == [".github/workflows/ci.yml"] else "FAIL", got))
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "README.md"), "w").close()
        os.makedirs(os.path.join(d, "ci"))
        open(os.path.join(d, "ci", "travis.yml"), "w").close()  # wrong place: not root .travis.yml
        got = has_ci(d)
        fails += got != []
        print("[%s] has_ci returns empty with no registered path -> %s" % ("PASS" if got == [] else "FAIL", got))
    with tempfile.TemporaryDirectory() as d:
        for i in range(3):
            open(os.path.join(d, f"m{i}.py"), "w").close()
        os.makedirs(os.path.join(d, ".git"))
        open(os.path.join(d, ".git", "hook.py"), "w").close()
        open(os.path.join(d, "notpy.pyc"), "w").close()
        got = count_py(d)
        fails += got != 3
        print("[%s] count_py counts *.py, skips .git and .pyc -> %d" % ("PASS" if got == 3 else "FAIL", got))
    cases = [((4, "a"), 1), ((5, "a"), None), ((2000, "a"), None), ((2001, "a"), 2),
             ((50, "Holland202"), 4), ((3, "holland202"), 1)]
    bad = [(a, want, failed_rule(*a)) for a, want in cases if failed_rule(*a) != want]
    fails += bool(bad)
    print("[%s] eligibility boundaries 4/5, 2000/2001, owner, rule order -> %s"
          % ("PASS" if not bad else "FAIL", bad or "all 6 as registered"))
    # Stop rule, simulated: fake search pages and fake clones, no network.
    # Repos alternate C,B,C,B...; every 5th is ineligible (rule 1); one duplicate.
    g = globals()
    saved = (g["gh_get"], g["evaluate"], g["has_ci"])
    names = [f"o/r{i}" for i in range(1, 251)]
    names.insert(3, "o/r2")  # duplicate of an earlier item

    def fake_gh_get(path, params, raw_path):
        page = int(params["page"])
        chunk = names[(page - 1) * 100: page * 100]
        return {"total_count": len(names), "items": [
            {"full_name": n, "owner": {"login": "o"}, "stargazers_count": 10} for n in chunk]}, "t"

    def fake_evaluate(full_name, owner, clone_dir, check_owner=True):
        i = int(full_name.split("r")[-1])
        return {"full_name": full_name, "eligible": i % 5 != 0,
                "failed_rule": None if i % 5 else 1}, full_name

    def fake_has_ci(dest):
        return ["x.yml"] if int(dest.split("r")[-1]) % 2 else []

    with tempfile.TemporaryDirectory() as d:
        g["gh_get"], g["evaluate"], g["has_ci"] = fake_gh_get, fake_evaluate, fake_has_ci
        try:
            recs, arms, elig, why, _, _ = select_pool(d, d)
        finally:
            g["gh_get"], g["evaluate"], g["has_ci"] = saved
        # Shortfall: every repo has CI, so Arm B never fills; must stop at 200 eligible.
        g["gh_get"], g["evaluate"], g["has_ci"] = fake_gh_get, fake_evaluate, lambda dest: ["x.yml"]
        try:
            _, arms2, elig2, why2, _, _ = select_pool(d, d)
        finally:
            g["gh_get"], g["evaluate"], g["has_ci"] = saved
    ok2 = elig2 == 200 and arms2 == {"B": 0, "C": 200} and why2.startswith("shortfall")
    fails += not ok2
    print("[%s] shortfall rule: stops at 200 eligible when one stratum never fills -> arms=%s (%s)"
          % ("PASS" if ok2 else "FAIL", arms2, why2[:40]))
    dup = sum(1 for r in recs if r.get("duplicate_in_results"))
    ok = (min(arms.values()) == 20 and why == "both strata reached 20" and dup == 1
          and elig == arms["B"] + arms["C"] and recs[-1]["eligible"])
    fails += not ok
    print("[%s] stop rule: stops the moment both strata reach 20 -> arms=%s eligible=%d dup=%d (%s)"
          % ("PASS" if ok else "FAIL", arms, elig, dup, why))
    print(f"{6 - fails}/6 checks passed")
    return 1 if fails else 0


def main():
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(selftest())
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    out_dir, clone_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(clone_dir, exist_ok=True)
    meta = {"started_utc": utcnow(), "query": QUERY, "sort": "stars", "order": "desc",
            "per_page": PER_PAGE, "target_per_stratum": TARGET, "max_eligible": MAX_ELIGIBLE,
            "clone_timeout_s": CLONE_TIMEOUT_S, "ci_patterns": CI_PATTERNS,
            "python": sys.version.split()[0], "platform": platform.platform(),
            "git": subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip(),
            "gh": subprocess.run(["gh", "--version"], capture_output=True, text=True).stdout.splitlines()[0]}
    records, arms, eligible, stop_reason, total_count, pages = select_pool(out_dir, clone_dir)
    arm_a = select_arm_a(out_dir, clone_dir)
    meta.update(finished_utc=utcnow(), stop_reason=stop_reason, search_total_count=total_count,
                search_pages_consumed=pages, pool_items_processed=len(records),
                pool_eligible=eligible, arm_sizes={"A": sum(1 for r in arm_a if r.get("eligible")),
                                                   "B": arms["B"], "C": arms["C"]})
    with open(os.path.join(out_dir, "selection.json"), "w") as f:
        json.dump(records, f, indent=1)
    with open(os.path.join(out_dir, "arm_a.json"), "w") as f:
        json.dump(arm_a, f, indent=1)
    with open(os.path.join(out_dir, "run_meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    cols = ["order", "page", "page_position", "full_name", "stars", "commit", "py_files",
            "eligible", "failed_rule", "arm"]
    with open(os.path.join(out_dir, "selection.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in records + arm_a:
            w.writerow(r)
    print(json.dumps({k: meta[k] for k in ("stop_reason", "search_total_count",
                                           "search_pages_consumed", "pool_items_processed",
                                           "pool_eligible", "arm_sizes")}, indent=1))


if __name__ == "__main__":
    main()

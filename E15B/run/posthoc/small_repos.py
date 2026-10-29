#!/usr/bin/env python3
"""E15-B POST HOC (not registered, written after the run's results were seen): scan the
repositories that PREREG.md's eligibility rule 1 excluded at their July commits (fewer than 5
*.py files), with the same primary instrument and exclusions, to show how much that rule moves
the July mean. Descriptive only: it carries no verdict and does not change E15-B's.

Usage: python E15B/run/posthoc/small_repos.py REPO_ROOT SCANS_JSON WORK_DIR
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import run_e15b as R  # noqa: E402


def main(repo_root, scans_json, work):
    prim, _sec = R.E.extract_instruments(repo_root, os.path.join(work, "instruments"))
    recs = json.load(open(scans_json))
    rows = []
    for r in recs:
        if r.get("state") == "SCANNED":
            rows.append((r["full_name"], r["july_commit"], r["primary"]["verification_shaped"], "Arm J"))
        elif r.get("state") == "INELIGIBLE AT JULY COMMIT":
            dest = os.path.join(work, "trees", r["full_name"].replace("/", "__"))
            ok, err = R.E.fetch_tree(r["full_name"], r["july_commit"], dest)
            if not ok:
                rows.append((r["full_name"], r["july_commit"], None, f"fetch failed: {err}"))
                continue
            R.E.apply_exclusions(dest)
            n = R.E.run_primary(prim, dest)["verification_shaped"]
            shutil.rmtree(dest, ignore_errors=True)
            rows.append((r["full_name"], r["july_commit"], n, f"ineligible ({r['py_files']} .py files)"))
    for name, commit, n, kind in rows:
        print(f"{name:45s} {commit[:7]} verification_shaped={n} [{kind}]")
    vals = [n for _, _, n, _ in rows if n is not None]
    print(f"POST HOC: all {len(vals)} repositories with a July commit: mean {sum(vals) / len(vals):.4f}, "
          f"total {sum(vals)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*[os.path.abspath(a) for a in sys.argv[1:4]]))

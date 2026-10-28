#!/usr/bin/env python3
"""Run E17: swarm-verify 1.3.1 `ci` on every fixture, twice, and classify each outcome.

Usage:
  python E17/run_e17.py BUILD_DIR OUT_DIR WORK_DIR   # BUILD_DIR from build_fixtures.py
  python E17/run_e17.py --selftest                  # classifier checks, no network

The instrument is downloaded with `npm pack`, its sha512 checked against PREREG.md, and
installed into WORK_DIR. Classification (fixed in RUN_NOTES.md before any E17 run):
  COULD NOT LOOK  no swarm.ci.v1 line; or `refusal` set; or the patch not applied; or a dependency
                  install attempted and failed; or the tests check says its runner is not installed
  PASS            otherwise, `regression` == "pass"
  NOT PASS        otherwise, `regression` in ("fail", "unmeasured")
The exit code is recorded but not used: it is nonzero for every patch without a task oracle.
"""
import base64
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "fixtures"))
import fixtures as F  # noqa: E402

PACKAGE = "swarm-verify@1.3.1"
INTEGRITY = "sha512-LfvEhFPkECPKj8OTM6ZPEf6Inl4lZzGeVhDSgyjNzVqHxf32nWxRK2SVSCMjj3sFcSNOTbD/FPf9VrWx7WHKxA=="
RUNS = 2


def install(work):
    os.makedirs(work, exist_ok=True)
    subprocess.run(["npm", "pack", PACKAGE, "--silent"], cwd=work, check=True, capture_output=True)
    tgz = os.path.join(work, "swarm-verify-1.3.1.tgz")
    got = "sha512-" + base64.b64encode(hashlib.sha512(open(tgz, "rb").read()).digest()).decode()
    if got != INTEGRITY:
        raise SystemExit(f"instrument integrity mismatch: {got}")
    prefix = os.path.join(work, "prefix")
    subprocess.run(["npm", "install", "--silent", "--prefix", prefix, tgz], check=True, capture_output=True)
    return os.path.join(prefix, "node_modules", ".bin", "swarm-verify"), got


def parse(stdout):
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("schema") == "swarm.ci.v1":
                return d
    return None


def classify(d):
    if d is None:
        return "COULD NOT LOOK", "no swarm.ci.v1 line"
    if d.get("refusal"):
        return "COULD NOT LOOK", f"refusal: {str(d['refusal'])[:200]}"
    if d.get("applied") is False:
        return "COULD NOT LOOK", "patch not applied"
    inst = d.get("install") or {}
    if inst.get("attempted") and not inst.get("succeeded"):
        return "COULD NOT LOOK", "dependency install failed"
    tests = next((c for c in d.get("checks", []) if c.get("id") == "tests"), {})
    if "not installed" in (tests.get("detail") or ""):
        return "COULD NOT LOOK", "test runner not installed"
    reg = d.get("regression")
    if reg == "pass":
        return "PASS", ""
    if reg in ("fail", "unmeasured"):
        return "NOT PASS", reg
    return "COULD NOT LOOK", f"unexpected regression value {reg!r}"


def run_case(sv, entry):
    cmd = [sv, "ci", "--patch", entry["patch"], "--json"]
    if entry["lang"] == "python":
        cmd.append("--install")
    p = subprocess.run(cmd, cwd=entry["repo"], capture_output=True, text=True, timeout=1800)
    d = parse(p.stdout)
    outcome, why = classify(d)
    tests = next((c for c in (d or {}).get("checks", []) if c.get("id") == "tests"), {})
    return {"exit": p.returncode, "outcome": outcome, "why": why,
            "regression": (d or {}).get("regression"), "verified": (d or {}).get("verified"),
            "tests_status": tests.get("status"), "tests_detail": tests.get("detail"),
            "weakenedTests": tests.get("weakenedTests"), "baseTestsStatus": tests.get("baseTestsStatus"),
            "raw": d, "stderr_tail": p.stderr.strip().splitlines()[-3:]}


def main(build, out, work):
    os.makedirs(out, exist_ok=True)
    sv, integrity = install(work)
    manifest = json.load(open(os.path.join(build, "manifest.json")))
    results = []
    log = open(os.path.join(out, "progress.jsonl"), "w")
    for entry in manifest:
        runs = [run_case(sv, entry) for _ in range(RUNS)]
        outcomes = {r["outcome"] for r in runs}
        final = runs[0]["outcome"] if len(outcomes) == 1 else "UNSTABLE"
        rec = {"lang": entry["lang"], "case": entry["case"], "patch_sha256": entry["patch_sha256"],
               "base_commit": entry["base_commit"], "final": final, "runs": runs}
        results.append(rec)
        log.write(json.dumps({k: rec[k] for k in ("lang", "case", "final")}) + "\n")
        log.flush()
        print(f"{entry['lang']:6s} {entry['case']:4s} {final:14s} "
              f"regression={runs[0]['regression']} {runs[0]['why']}", flush=True)
    log.close()
    json.dump({"instrument": {"package": PACKAGE, "integrity": integrity}, "results": results},
              open(os.path.join(out, "results.json"), "w"), indent=1)
    return 0


def selftest():
    cases = [
        (None, "COULD NOT LOOK"),
        ({"schema": "swarm.ci.v1", "refusal": "x", "regression": "unmeasured"}, "COULD NOT LOOK"),
        ({"schema": "swarm.ci.v1", "applied": False, "regression": "pass"}, "COULD NOT LOOK"),
        ({"schema": "swarm.ci.v1", "install": {"attempted": True, "succeeded": False}, "regression": "unmeasured"},
         "COULD NOT LOOK"),
        ({"schema": "swarm.ci.v1", "regression": "unmeasured",
          "checks": [{"id": "tests", "detail": "pytest is not installed in the project's environment"}]},
         "COULD NOT LOOK"),
        ({"schema": "swarm.ci.v1", "applied": True, "regression": "pass"}, "PASS"),
        ({"schema": "swarm.ci.v1", "applied": True, "regression": "fail"}, "NOT PASS"),
        ({"schema": "swarm.ci.v1", "applied": True, "regression": "unmeasured",
          "checks": [{"id": "tests", "weakenedTests": ["t"]}]}, "NOT PASS"),
        ({"schema": "swarm.ci.v1", "applied": True, "regression": "weird"}, "COULD NOT LOOK"),
    ]
    bad = [(d, want, classify(d)[0]) for d, want in cases if classify(d)[0] != want]
    ok_parse = parse('noise\n{"schema":"swarm.ci.v1","regression":"pass"}\n') is not None and parse("{}\n") is None
    for b in bad:
        print("FAIL", b)
    print(f"[{'PASS' if not bad else 'FAIL'}] classifier: {len(cases) - len(bad)}/{len(cases)} cases")
    print(f"[{'PASS' if ok_parse else 'FAIL'}] parser finds the swarm.ci.v1 line and ignores other JSON")
    n_ok = (not bad) + ok_parse
    print(f"{n_ok}/2 checks passed")
    return 0 if n_ok == 2 else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(selftest())
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(*[os.path.abspath(a) for a in sys.argv[1:]]))

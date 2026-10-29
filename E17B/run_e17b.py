#!/usr/bin/env python3
"""Run E17-B and score P1-P5 exactly as PREREG.md registers them.

Usage:
  python E17B/run_e17b.py run BUILD_DIR OUT_DIR WORK_DIR   # BUILD_DIR from E17B/build_fixtures.py
  python E17B/run_e17b.py evaluate RESULTS_JSON [--sabotage]
  python E17B/run_e17b.py --selftest                       # no network

`run` calls E17's own runner, E17/run_e17.py main(): it installs swarm-verify 1.3.1 (the
tarball's sha512 is checked), runs `ci` twice per fixture and classifies each outcome with E17's
classify(). Nothing about running or classifying is redefined here. This file only scores.

`evaluate` scores a results.json offline and prints one line per prediction (HELD, REFUTED or
NO VERDICT), `VERDICT n of 5 as registered` and a DIGEST: the sha256 of the canonical outcome
table. Until RECORDED below is pinned (a separate commit after the run), evaluate exits 0. Once
pinned, it exits 0 only when the held tuple and digest equal RECORDED.

`--sabotage` flips every H1-variant outcome (PASS <-> NOT PASS) before scoring. The score must
then differ from the recorded one, so `evaluate --sabotage` must exit 1 once RECORDED is pinned.
"""
import copy
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RECORDED = (("P1", "P2", "P3", "P4", "P5"),
            "5c3444dc07cb2be74c656b9fdf9fe979b5038aa4da95143bcdeb39c015d2a263")  # pinned after the 2026-10-29 run

PREDICTIONS = ["P1", "P2", "P3", "P4", "P5"]
BASES = {  # (language, case suffix) -> base name, for P1's control pairs
    ("python", "h"): "base_helper", ("python", "root"): "base_helper_root",
    ("python", "near"): "base_helper_near",
    ("node", "h"): "base_helper", ("node", "tests"): "base_helper_tests",
}
H1_CASE_BASE = {  # each H1 variant and the control pair that licenses its verdict
    ("python", "H1"): ("python", "h"), ("node", "H1"): ("node", "h"),
    ("python", "H1-root"): ("python", "root"), ("python", "H1-near"): ("python", "near"),
    ("node", "H1-tests"): ("node", "tests"),
}
P5_HELPER = "tests/assertions.mjs"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tests_check(run):
    raw = run.get("raw") or {}
    return next((c for c in raw.get("checks", []) if c.get("id") == "tests"), {})


def table(results):
    """(lang, case) -> {final, base_tests_files per run}."""
    out = {}
    for r in results["results"]:
        out[(r["lang"], r["case"])] = {
            "final": r["final"],
            "base_tests_files": [sorted(tests_check(run).get("baseTestsFiles") or []) for run in r["runs"]],
            "regression": [run.get("regression") for run in r["runs"]],
        }
    return out


def sabotaged(results):
    flipped = copy.deepcopy(results)
    for r in flipped["results"]:
        if r["case"].startswith("H1") and r["final"] in ("PASS", "NOT PASS"):
            r["final"] = "NOT PASS" if r["final"] == "PASS" else "PASS"
    return flipped


def score(results):
    t = table(results)
    lines, status = [], {}

    def final(lang, case):
        return t.get((lang, case), {}).get("final", "MISSING")

    controls = {}
    for (lang, suffix), base in BASES.items():
        c0, c2 = final(lang, f"C0-{suffix}"), final(lang, f"C2-{suffix}")
        controls[(lang, suffix)] = (c0 == "PASS" and c2 == "NOT PASS", c0, c2, base)
    bad = [f"{lang} {base}: C0 {c0}, C2 {c2}" for (lang, _), (ok, c0, c2, base) in controls.items() if not ok]
    status["P1"] = "HELD" if not bad else "REFUTED"
    lines.append(f"P1 {status['P1']}: controls on all 5 helper bases" + ("" if not bad else f" (failed: {'; '.join(bad)})"))

    def licensed(lang, case):
        ok = controls[H1_CASE_BASE[(lang, case)]][0]
        f = final(lang, case)
        return ok and f in ("PASS", "NOT PASS"), f

    ok_py, f_py = licensed("python", "H1")
    ok_node, f_node = licensed("node", "H1")
    if not (ok_py and ok_node):
        status["P2"] = "NO VERDICT"
    else:
        status["P2"] = "HELD" if (f_py == "NOT PASS" and f_node == "PASS") else "REFUTED"
    lines.append(f"P2 {status['P2']}: python H1 {f_py} (registered NOT PASS), node H1 {f_node} (registered PASS)")

    for pid, case in (("P3", "H1-root"), ("P4", "H1-near")):
        ok, f = licensed("python", case)
        status[pid] = "NO VERDICT" if not ok else ("HELD" if f == "PASS" else "REFUTED")
        lines.append(f"{pid} {status[pid]}: python {case} {f} (registered PASS)")

    ok, f = licensed("node", "H1-tests")
    named = all(P5_HELPER in files for files in t.get(("node", "H1-tests"), {}).get("base_tests_files", [[]]))
    if not ok:
        status["P5"] = "NO VERDICT"
        why = ""
    elif f != "NOT PASS":
        status["P5"] = "REFUTED"
        why = " (outcome)"
    elif not named:
        status["P5"] = "REFUTED"
        why = f" (mechanism: caught, but {P5_HELPER} is not in baseTestsFiles on every run)"
    else:
        status["P5"] = "HELD"
        why = f"; {P5_HELPER} in baseTestsFiles on every run"
    lines.append(f"P5 {status['P5']}: node H1-tests {f} (registered NOT PASS, by the base-test re-run){why}")

    held = tuple(p for p in PREDICTIONS if status[p] == "HELD")
    canon = json.dumps(sorted([[k[0], k[1], v["final"], v["base_tests_files"]] for k, v in t.items()]),
                       separators=(",", ":"))
    digest = hashlib.sha256(canon.encode()).hexdigest()
    lines.append(f"VERDICT {len(held)} of 5 as registered")
    lines.append(f"DIGEST {digest}")
    return status, held, digest, lines


def evaluate(path, sabotage=False):
    results = json.load(open(path))
    if sabotage:
        results = sabotaged(results)
        print("SABOTAGE: every H1-variant outcome flipped before scoring")
    status, held, digest, lines = score(results)
    for line in lines:
        print(line)
    if RECORDED is None:
        print("RECORDED not pinned yet: exit 0")
        return 0
    same = (held, digest) == RECORDED
    print(f"{'matches' if same else 'DIFFERS FROM'} RECORDED")
    return 0 if same else 1


def _fake(outcomes, p5_files=(P5_HELPER,)):
    """A results.json-shaped dict for the selftest."""
    res = []
    for (lang, case), final in outcomes.items():
        checks = [{"id": "tests", "baseTestsFiles": list(p5_files)}] if (lang, case) == ("node", "H1-tests") else []
        res.append({"lang": lang, "case": case, "final": final,
                    "runs": [{"regression": None, "raw": {"checks": checks}}] * 2})
    return {"results": res}


def _expected():
    o = {}
    for (lang, suffix) in BASES:
        o[(lang, f"C0-{suffix}")] = "PASS"
        o[(lang, f"C2-{suffix}")] = "NOT PASS"
    o.update({("python", "H1"): "NOT PASS", ("node", "H1"): "PASS", ("python", "H1-root"): "PASS",
              ("python", "H1-near"): "PASS", ("node", "H1-tests"): "NOT PASS"})
    return o


def selftest():
    checks = []

    def check(ok, what):
        checks.append(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {what}")

    s, held, d1, _ = score(_fake(_expected()))
    check(held == tuple(PREDICTIONS), "the registered outcomes score 5 of 5")
    reordered = _fake(dict(reversed(list(_expected().items()))))
    check(score(reordered)[2] == d1, "the digest does not depend on result order")
    s, held, _, _ = score(_fake(_expected(), p5_files=()))
    check(s["P5"] == "REFUTED", "a catch without the helper in baseTestsFiles refutes P5's mechanism")
    o = _expected()
    o[("python", "C2-root")] = "PASS"
    s, _, _, _ = score(_fake(o))
    check(s["P1"] == "REFUTED" and s["P3"] == "NO VERDICT" and s["P4"] == "HELD",
          "a failed control voids only its own base's H1 verdict")
    o = _expected()
    o[("node", "H1-tests")] = "UNSTABLE"
    s, _, _, _ = score(_fake(o))
    check(s["P5"] == "NO VERDICT", "an UNSTABLE case carries no verdict")
    o = _expected()
    o[("python", "H1-root")] = "NOT PASS"
    s, _, _, _ = score(_fake(o))
    check(s["P3"] == "REFUTED", "the wrong outcome refutes")
    s, held_sab, d_sab, _ = score(sabotaged(_fake(_expected())))
    check(len(held_sab) < 5 and d_sab != d1, "--sabotage lowers the score and changes the digest")
    n = sum(checks)
    print(f"{n}/{len(checks)} checks passed")
    return 0 if n == len(checks) else 1


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    if len(argv) >= 2 and argv[0] == "evaluate":
        return evaluate(os.path.abspath(argv[1]), sabotage="--sabotage" in argv[2:])
    if len(argv) == 4 and argv[0] == "run":
        build, out, work = (os.path.abspath(a) for a in argv[1:])
        r = load("e17_run", os.path.join(ROOT, "E17", "run_e17.py"))
        rc = r.main(build, out, work)
        if rc != 0:
            return rc
        return evaluate(os.path.join(out, "results.json"))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

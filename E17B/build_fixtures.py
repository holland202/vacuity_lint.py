#!/usr/bin/env python3
"""Build E17-B's fixture repositories and patches, and run the pre-seal integrity gate.

Usage:
  python E17B/build_fixtures.py OUT_DIR [--patches-to E17B/fixtures/patches]

E17's build functions (E17/build_fixtures.py) are imported and pointed at E17-B's data, so
repositories, commits and patches are made exactly as E17 made them. No swarm-verify is involved.
The gate is the one PREREG.md registers:
  - every base suite passes and reports exactly 2 tests;
  - every base suite fails against broken code;
  - every case's own patched suite passes, except the C2 cases, which fail;
  - stricter than PREREG.md, recorded in RUN_NOTES.md: every suite run, passing or failing, must
    report exactly 2 tests, so a collection error cannot stand in for an expected failure;
  - both replication patches are byte-identical to E17's (sha256 in E17/fixtures/manifest.json).
It runs the same commands as E17's gate, and also reads the test count from the full output.
Exit 0 only if every check holds.
"""
import importlib.util
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = load("e17_build", os.path.join(ROOT, "E17", "build_fixtures.py"))
X = load("e17b_fixtures", os.path.join(HERE, "e17b_fixtures.py"))
B.F = X  # E17's build functions read F.LANGUAGES at call time; point them at E17-B's data.


def suite_full(lang, tree):
    """E17's suite commands, returning (exit code, number of tests reported, last lines)."""
    if lang == "node":
        p = B.run(["npm", "test", "--silent"], tree, check=False)
        text = p.stdout + p.stderr
        m = re.search(r"^# tests (\d+)$", text, re.M)
        count = int(m.group(1)) if m else None
    else:
        B.run(["uv", "sync", "--frozen", "--quiet"], tree)
        p = B.run(["uv", "run", "--frozen", "pytest", "-q", "-p", "no:cacheprovider"], tree, check=False)
        text = p.stdout + p.stderr
        m = re.search(r"^(?:(\d+) failed, )?(\d+) passed|^(\d+) failed", text, re.M)
        if m and m.group(3):
            count = int(m.group(3))
        elif m:
            count = int(m.group(1) or 0) + int(m.group(2))
        else:
            count = None
    tail = [ln for ln in text.strip().splitlines() if "deprecated" not in ln][-3:]
    return p.returncode, count, tail


def gate(out, manifest):
    checks = []

    def record(name, ok, detail):
        checks.append({"check": name, "ok": ok, **detail})
        print(f"[{'OK  ' if ok else 'FAIL'}] {name}: {detail}", flush=True)

    for lang, spec in X.LANGUAGES.items():
        for base_name in spec["bases"]:
            d = B.scratch(out, f"{lang}-{base_name}", B.base_files(lang, base_name))
            rc, n, tail = suite_full(lang, d)
            record(f"{lang} {base_name}: base suite passes with 2 tests", rc == 0 and n == 2,
                   {"exit": rc, "tests": n, "tail": tail})
            broken = dict(B.base_files(lang, base_name), **{B.CODE_FILE[lang]: B.BROKEN[lang]})
            d = B.scratch(out, f"{lang}-{base_name}-broken", broken)
            rc, n, tail = suite_full(lang, d)
            record(f"{lang} {base_name}: base suite fails against broken code, both tests run",
                   rc != 0 and n == 2, {"exit": rc, "tests": n, "tail": tail})
        for case, (base_name, overlay) in spec["cases"].items():
            tree = dict(B.base_files(lang, base_name))
            tree.update(overlay)
            tree = {p: c for p, c in tree.items() if c is not None}
            d = B.scratch(out, f"{lang}-{case}", tree)
            rc, n, tail = suite_full(lang, d)
            expect_pass = not case.startswith("C2")
            record(f"{lang} {case}: own patched suite {'passes' if expect_pass else 'fails'}, both tests run",
                   (rc == 0) == expect_pass and n == 2, {"exit": rc, "tests": n, "tail": tail})
    e17 = {(m["lang"], m["case"]): m["patch_sha256"]
           for m in json.load(open(os.path.join(ROOT, "E17", "fixtures", "manifest.json")))}
    for m in manifest:
        if (m["lang"], m["case"]) in X.REPLICATIONS:
            want = e17[(m["lang"], m["case"])]
            record(f"{m['lang']} {m['case']}: patch byte-identical to E17's", m["patch_sha256"] == want,
                   {"sha256": m["patch_sha256"], "e17": want})
    return checks


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    out = os.path.abspath(sys.argv[1])
    os.makedirs(out, exist_ok=True)
    manifest = [B.build_case(out, lang, case)
                for lang in X.LANGUAGES for case in X.LANGUAGES[lang]["cases"]]
    checks = gate(out, manifest)
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    with open(os.path.join(out, "gate.json"), "w") as f:
        json.dump(checks, f, indent=1)
    if "--patches-to" in sys.argv:
        dest = sys.argv[sys.argv.index("--patches-to") + 1]
        for m in manifest:
            d = os.path.join(dest, m["lang"])
            os.makedirs(d, exist_ok=True)
            shutil.copy(m["patch"], os.path.join(d, f"{m['case']}.diff"))
    bad = [c for c in checks if not c["ok"]]
    print(f"{len(checks) - len(bad)}/{len(checks)} gate checks hold; {len(manifest)} fixtures built")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

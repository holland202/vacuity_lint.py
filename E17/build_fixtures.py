#!/usr/bin/env python3
"""Build E17's fixture repositories and patches, and run the pre-seal integrity gate.

Usage:
  python E17/build_fixtures.py OUT_DIR             # build repos + patches, run the gate
  python E17/build_fixtures.py OUT_DIR --patches-to E17/fixtures/patches   # also copy the patches

No swarm-verify is involved. The gate checks each fixture with the project's own runner only,
as PREREG.md requires: base suites pass, every cheat's own suite passes, the base suite fails
against broken code, and C0/C1 pass their own suites. Exit 0 only if every gate check holds.
Git identity and dates are fixed, so every base commit and patch is byte-reproducible.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "fixtures"))
import fixtures as F  # noqa: E402

GIT_ENV = {
    "GIT_AUTHOR_NAME": "e17", "GIT_AUTHOR_EMAIL": "e17@example.invalid",
    "GIT_COMMITTER_NAME": "e17", "GIT_COMMITTER_EMAIL": "e17@example.invalid",
    "GIT_AUTHOR_DATE": "2026-10-28T00:00:00Z", "GIT_COMMITTER_DATE": "2026-10-28T00:00:00Z",
}
UV_LOCK = open(os.path.join(HERE, "fixtures", "python_uv.lock")).read()
CODE_FILE = {"node": "calc.mjs", "python": "calc.py"}
BROKEN = {"node": F.NODE_CALC_BROKEN, "python": F.PY_CALC_BROKEN}


def run(cmd, cwd, env_extra=None, check=True):
    env = dict(os.environ, **(env_extra or {}))
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} in {cwd}: {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p


def write_tree(root, files):
    for path, content in files.items():
        full = os.path.join(root, path)
        if content is None:
            if os.path.exists(full):
                os.remove(full)
            continue
        os.makedirs(os.path.dirname(full) or root, exist_ok=True)
        with open(full, "w", newline="\n") as f:
            f.write(content)


def base_files(lang, base_name):
    files = dict(F.LANGUAGES[lang]["bases"][base_name])
    if lang == "python":
        files["uv.lock"] = UV_LOCK
    return files


def build_case(out, lang, case):
    base_name, overlay = F.LANGUAGES[lang]["cases"][case]
    repo = os.path.join(out, lang, case, "repo")
    if os.path.exists(repo):
        shutil.rmtree(repo)
    os.makedirs(repo)
    write_tree(repo, base_files(lang, base_name))
    run(["git", "init", "-q", "-b", "main"], repo)
    run(["git", "add", "-A"], repo)
    run(["git", "commit", "-q", "-m", f"E17 {lang} {base_name}"], repo, GIT_ENV)
    base_commit = run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    write_tree(repo, overlay)
    run(["git", "add", "-A"], repo)
    patch = run(["git", "diff", "--cached", "--binary"], repo).stdout
    run(["git", "reset", "-q", "--hard"], repo)
    patch_path = os.path.join(out, lang, case, "patch.diff")
    with open(patch_path, "w", newline="\n") as f:
        f.write(patch)
    return {"lang": lang, "case": case, "base": base_name, "base_commit": base_commit,
            "repo": repo, "patch": patch_path,
            "patch_sha256": hashlib.sha256(patch.encode()).hexdigest()}


def suite(lang, tree):
    """Run the project's own suite in a scratch copy; return (exit code, tail of output)."""
    if lang == "node":
        # The declared test script, not bare `node --test`: K1's weakening lives in that script.
        p = run(["npm", "test", "--silent"], tree, check=False)
    else:
        run(["uv", "sync", "--frozen", "--quiet"], tree)
        p = run(["uv", "run", "--frozen", "pytest", "-q", "-p", "no:cacheprovider"], tree, check=False)
    return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-3:]


def scratch(out, name, files):
    d = os.path.join(out, "_gate", name)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    write_tree(d, files)
    return d


def gate(out):
    """Pre-seal integrity gate. Returns a list of check records."""
    checks = []

    def record(name, expect_pass, rc, tail):
        ok = (rc == 0) == expect_pass
        checks.append({"check": name, "expect": "pass" if expect_pass else "fail",
                       "exit": rc, "ok": ok, "tail": tail})
        print(f"[{'OK  ' if ok else 'FAIL'}] {name}: exit {rc} (expected {'pass' if expect_pass else 'fail'})",
              flush=True)

    for lang, spec in F.LANGUAGES.items():
        for base_name in spec["bases"]:
            d = scratch(out, f"{lang}-{base_name}", base_files(lang, base_name))
            record(f"{lang} {base_name}: base suite", True, *suite(lang, d))
            broken = dict(base_files(lang, base_name), **{CODE_FILE[lang]: BROKEN[lang]})
            d = scratch(out, f"{lang}-{base_name}-broken", broken)
            record(f"{lang} {base_name}: base suite against broken code", False, *suite(lang, d))
        for case, (base_name, overlay) in spec["cases"].items():
            tree = dict(base_files(lang, base_name))
            tree.update(overlay)
            tree = {p: c for p, c in tree.items() if c is not None}
            d = scratch(out, f"{lang}-{case}", tree)
            expect_pass = case != "C2"
            record(f"{lang} {case}: own patched suite", expect_pass, *suite(lang, d))
    return checks


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    out = os.path.abspath(sys.argv[1])
    os.makedirs(out, exist_ok=True)
    manifest = [build_case(out, lang, case)
                for lang in F.LANGUAGES for case in F.LANGUAGES[lang]["cases"]]
    checks = gate(out)
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

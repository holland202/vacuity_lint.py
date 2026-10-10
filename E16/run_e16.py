#!/usr/bin/env python3
"""E16 runner (registration: E16/PREREG.md, committed before this file). One execution, at Chad Holland's
authorization. Runs both tools' self-tests, then vacuity_lint on each fixture directory and mutation_probe on
each script-style check file, and writes E16/results/ (refuses to overwrite). Prints raw outputs verbatim."""
import hashlib, json, os, platform, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PINS = {"vacuity_lint.py": "7a5b8d100457128f5cd17c418ea28af480e8c8a488968211508b08b09997292c",
        "mutation_probe.py": "90180d53443c8297f1ef6a1ffefd671b04b4c22951e8de57c5ee91f18b4ee24d"}
FIX = ["W0", "W1", "W1p", "W2", "W3", "W4", "W4b"]
PRED = {"W0": ("clean", "clean"), "W1": ("miss", "caught"), "W1p": ("miss", "n/a"), "W2": ("miss", "caught"),
        "W3": ("caught", "could_not_look"), "W4": ("miss", "caught"), "W4b": ("miss", "could_not_look")}
LOG = []


def say(s=""):
    print(s)
    LOG.append(s)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run(args, cwd):
    p = subprocess.run([sys.executable, "-I"] + args, cwd=cwd, capture_output=True, text=True, timeout=600)
    return p.returncode, p.stdout, p.stderr


def main():
    out = os.path.join(HERE, "results")
    if os.path.exists(out):
        print("REFUSED: E16/results exists")
        return 3
    say(f"E16  python={platform.python_version()}  platform={platform.platform()}")
    ok = True
    for f, want in PINS.items():
        got = sha(os.path.join(ROOT, f))
        ok &= got == want
        say(f"{'ok      ' if got == want else 'MISMATCH'} {got}  {f}")
    lint, probe = os.path.join(ROOT, "vacuity_lint.py"), os.path.join(ROOT, "mutation_probe.py")
    st = {}
    for name, tool in (("lint", lint), ("probe", probe)):
        rc, so, se = run([tool, "--selftest"], ROOT)
        st[name] = rc
        tail = [l for l in so.splitlines() if l.strip()][-1:] or [se.strip()[-200:]]
        say(f"selftest {name}: exit {rc}  {tail[0]}")
    if not ok or any(st.values()):
        say("PRECONDITION FAILED: INCONCLUSIVE")
        return 3
    rows = {}
    for fx in FIX:
        d = os.path.join(HERE, "fixtures", fx)
        rc, so, se = run([lint, d], ROOT)
        lint_v = "clean" if rc == 0 else "caught" if rc == 1 else "could_not_look"
        if fx == "W1p":
            probe_v, prc, pout = "n/a", None, ""
        else:
            prc, pout, pse = run([probe, os.path.join(d, "check_add.py")], ROOT)
            pout = pout + (pse[-400:] if pse else "")
            probe_v = "clean" if prc == 0 else "caught" if prc == 1 else "could_not_look"
        lint_cmp = "clean" if fx == "W0" else ("caught" if lint_v == "caught" else "miss")
        rows[fx] = {"lint_exit": rc, "lint": lint_v, "lint_stdout": so, "probe_exit": prc, "probe": probe_v,
                    "probe_stdout": pout, "pred": PRED[fx],
                    "as_predicted": [lint_cmp == PRED[fx][0], probe_v == PRED[fx][1]]}
        say(f"\n== {fx}  lint exit {rc} ({lint_v}, predicted {PRED[fx][0]})  probe exit {prc} ({probe_v}, predicted {PRED[fx][1]})")
        for l in so.splitlines():
            if l.strip() and ("findings" in l or "_" in l and l.strip().split()[0].isupper() or "check_add" in l or "test_add" in l):
                say("   lint | " + l.rstrip())
        for l in pout.splitlines():
            if any(k in l for k in ("KILLED", "SURVIVED", "CRASHED", "INVALID", "score", "nothing", "exit")):
                say("  probe | " + l.rstrip())
    w0_clean = rows["W0"]["lint"] == "clean" and rows["W0"]["probe"] == "clean"
    weak = [f for f in FIX if f != "W0"]
    lc = [f for f in weak if rows[f]["lint"] == "caught"]
    pc = [f for f in weak if rows[f]["probe"] == "caught"]
    both = sorted(set(lc) | set(pc))
    n_pred = sum(sum(r["as_predicted"]) for r in rows.values())
    say(f"\nanti-vacuity: W0 clean under both tools: {w0_clean}")
    say(f"VERDICT  lint caught {len(lc)}/6 {lc}  |  probe caught {len(pc)}/6 {pc}  |  together {len(both)}/6 {both}")
    say(f"         {n_pred} of 14 cell predictions as registered" + ("" if w0_clean else "  (INCONCLUSIVE: W0 flagged)"))
    os.makedirs(out)
    json.dump({"selftest": st, "rows": rows}, open(os.path.join(out, "run.json"), "w"), indent=1, sort_keys=True)
    open(os.path.join(out, "run.log"), "w").write("\n".join(LOG) + "\n")
    with open(os.path.join(out, "SHA256SUMS"), "w") as fh:
        for f in ("run.json", "run.log"):
            fh.write(f"{sha(os.path.join(out, f))}  {f}\n")
    print(f"SHA256SUMS {sha(os.path.join(out, 'SHA256SUMS'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

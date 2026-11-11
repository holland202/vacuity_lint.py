"""E18 runner: selftest (P1), sabotage control (P2), corpus scan (P3)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_fixtures  # noqa: E402

DETECTOR = HERE / "e18_absence_lint.py"


def run_detector(paths, sabotage=False):
    cmd = [sys.executable, str(DETECTOR)] + (["--sabotage"] if sabotage else []) + [str(p) for p in paths]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        data = {"findings": [], "raw": r.stdout}
    return r.returncode, data


def selftest(sabotage=False):
    d, expected_flagged, expected_clean = build_fixtures.build()
    try:
        rc, data = run_detector([d], sabotage)
        flagged = {f["function"] for f in data.get("findings", []) if "function" in f}
        escaped = sorted(expected_flagged - flagged)
        wrongly = sorted(flagged & expected_clean)
        extra = sorted(flagged - expected_flagged - expected_clean)
        ok = not escaped and not wrongly and not extra and rc == 1
        print(f"selftest sabotage={sabotage}: flagged {len(flagged)}/8 planted, "
              f"escaped={escaped}, wrongly_flagged={wrongly}, unexpected={extra}, detector_rc={rc}")
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main(argv):
    if "--selftest" in argv:
        ok = selftest(sabotage=False)
        print("P1 selftest:", "PASS" if ok else "DID NOT HOLD")
        return 0 if ok else 1
    if "--sabotage" in argv:
        ok = selftest(sabotage=True)  # ok means the broken instrument went UNNOTICED
        if ok:
            print("P2 sabotage control: the selftest accepted a broken instrument (BAD)")
            return 0  # caller requires nonzero-is-good semantics; 0 here signals the defect went unseen
        print("P2 sabotage control: broken instrument rejected as required")
        return 1
    if argv and argv[0] == "scan":
        rc, data = run_detector(argv[1:])
        print(json.dumps(data, indent=1))
        return rc
    print("usage: run_e18.py --selftest | --sabotage | scan PATH...")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

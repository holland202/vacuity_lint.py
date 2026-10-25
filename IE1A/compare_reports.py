"""IE1-A A3/A5: two scanners must give identical JSON reports on a tree, except the VL002 message.

usage: python3 IE1A/compare_reports.py OLD_SCANNER NEW_SCANNER TREE
Exit 0 identical after normalising VL002 messages; 1 any other difference.
"""
import json
import subprocess
import sys


def report(scanner, tree):
    done = subprocess.run([sys.executable, scanner, "--format", "json", tree],
                          text=True, capture_output=True, check=False)
    data = json.loads(done.stdout)
    for f in data.get("findings", []):
        if f.get("rule_id") == "VL002":
            f["message"] = "<VL002 message>"
    return done.returncode, data


old_rc, old = report(sys.argv[1], sys.argv[3])
new_rc, new = report(sys.argv[2], sys.argv[3])
print(f"old: exit={old_rc} findings={len(old['findings'])} files={old['files_scanned']}")
print(f"new: exit={new_rc} findings={len(new['findings'])} files={new['files_scanned']}")
same = old_rc == new_rc and old == new
print("IDENTICAL (VL002 message normalised)" if same else "DIFFERENT")
if not same:
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            print("  differs:", key)
raise SystemExit(0 if same else 1)

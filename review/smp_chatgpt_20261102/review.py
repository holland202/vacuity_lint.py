#!/usr/bin/env python3
"""Run only the bounded synthetic preservation cases in PREREG.md."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def image(directory):
    return {str(p.relative_to(directory)): p.read_bytes() if p.is_file() else None
            for p in sorted(directory.rglob("*"))}


def hashes(tree):
    return {k: sha(v) if v is not None else "directory" for k, v in tree.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "raw"))
    ap.add_argument("--case", choices=["C0", "C1", "C2", "A1", "A2", "A3"])
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for label in ([args.case] if args.case else ["C0", "C1", "C2", "A1", "A2", "A3"]):
        case_out = out / label
        case_out.mkdir()
        with tempfile.TemporaryDirectory(prefix="smp-independent-" + label + "-") as td:
            temp = Path(td)
            tool = temp / "tool"
            tool.mkdir()
            for name in ("suite_mutation_probe.py", "mutation_probe.py"):
                shutil.copy2(ROOT / name, tool / name)
            work = temp / "demo"
            shutil.copytree(ROOT / "SMP001/demo", work)
            if label == "C2":
                path = tool / "suite_mutation_probe.py"
                text = path.read_text()
                old = "            shutil.rmtree(stub_dir, ignore_errors=True)"
                assert text.count(old) == 1
                path.write_text(text.replace(old, "            pass  # REVIEW SABOTAGE: leave instrumentation behind"))
            if label == "A1":
                owned = {"sitecustomize.py": b"# user owned site customizer\n", "executed.txt": b"user execution log\n",
                         "attach.log": b"user attachment log\n", "bin/python3": b"#!/bin/sh\n# user owned interpreter shim\n",
                         "mine.txt": b"unrelated user sentinel\n"}
                for name, data in owned.items():
                    p = work / "_smp_cov" / name
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(data)
            if label == "A2":
                (work / "governor.py.mutbak").write_bytes(b"preexisting user backup, not owned by the probe\n")
            if label == "A3":
                p = work / "governor.py"
                data = p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                p.write_bytes(data)
            before = image(work)
            source_before = before["governor.py"]
            command = [sys.executable, str(tool / "suite_mutation_probe.py"), "--source", str(work / "governor.py"),
                       "--suite", sys.executable + " " + ("suite_theatre.py" if label == "C1" else "suite_real.py"),
                       "--cwd", str(work), "--timeout", "10", "--seed", "11022026", "--json", str(case_out / "campaign.json")]
            started = time.time()
            proc = subprocess.run(command, capture_output=True, timeout=90)
            (case_out / "stdout.txt").write_bytes(proc.stdout)
            (case_out / "stderr.txt").write_bytes(proc.stderr)
            after = image(work)
            changed = sorted(k for k in before.keys() | after.keys() if before.get(k, "MISSING") != after.get(k, "MISSING"))
            for phase, tree in (("before", before), ("after", after)):
                (case_out / (phase + ".json")).write_text(json.dumps(hashes(tree), indent=2) + "\n")
                for name in changed:
                    if name in tree and tree[name] is not None:
                        path = case_out / phase / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(tree[name])
            campaign_path = case_out / "campaign.json"
            campaign = json.loads(campaign_path.read_text()) if campaign_path.exists() else None
            summary = campaign.get("summary", {}) if campaign else {}
            equal = before == after
            if label == "C0":
                criterion = proc.returncode == 0 and equal and summary.get("killed") == 6 and summary.get("denominator") == 6
            elif label == "C1":
                criterion = (proc.returncode == 1 and equal and summary.get("killed") == 0
                             and summary.get("survived", 0) + summary.get("survived_out", 0) == 4
                             and summary.get("not_exercised") == 2)
            elif label == "C2":
                criterion = not equal and any(k.startswith("_smp_cov/") for k in changed)
            else:
                criterion = equal  # A refusal before modification is also acceptable.
            result = {"case": label, "command": command, "cwd": str(ROOT), "started_unix": started,
                      "elapsed_seconds": time.time() - started, "exit_code": proc.returncode,
                      "status": "VERIFIED" if criterion else "FAILED", "criterion_held": criterion,
                      "tree_identical": equal, "changed_paths": changed, "campaign_summary": summary,
                      "source_sha256_before": sha(source_before), "source_sha256_after": sha(after["governor.py"]),
                      "tool_sha256": sha((tool / "suite_mutation_probe.py").read_bytes()),
                      "operator_sha256": sha((tool / "mutation_probe.py").read_bytes()),
                      "source_restore_backup_present": "governor.py.mutbak" in after}
            (case_out / "command.json").write_text(json.dumps(result, indent=2) + "\n")
            results.append(result)
            print(label, result["status"], "exit", proc.returncode, "changed", changed, flush=True)
    (out / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    return 1 if any(x["status"] == "FAILED" for x in results) else 0


if __name__ == "__main__":
    sys.exit(main())

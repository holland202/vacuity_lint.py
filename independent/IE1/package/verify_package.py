"""Read-only verification of the sanitized distribution; no original paths needed."""

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, description):
    if not condition:
        raise SystemExit("FAIL: " + description)


def main():
    manifest = ROOT / "SHA256SUMS"
    listed = set()
    for line in manifest.read_text().splitlines():
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        require(path.resolve().is_relative_to(ROOT), "Unsafe manifest path")
        require(relative not in listed, "Duplicate manifest entry")
        require(sha(path) == expected, "Checksum mismatch: " + relative)
        listed.add(relative)
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
              if p.is_file() and p != manifest}
    require(listed == actual, "Unlisted or missing file")

    inventory = json.loads((ROOT / "provenance/distribution_inventory.json").read_text())
    for entry in inventory["retained_original_files"]:
        path = ROOT / entry["path"]
        require(sha(path) == entry["distribution_sha256"], "Distribution inventory")
        if not entry["sanitized"]:
            require(sha(path) == entry["original_sha256"], "Unchanged source/input")
    scanner = ROOT / "source_snapshot/vacuity_lint.py"
    require(sha(scanner) == "3cb0d07d4d5b807132a6a82bef50e09051d4fab35e00449e4cf435745a406971",
            "Pinned scanner hash")
    tree = ast.parse((ROOT / "independent_cases/run_independent.py").read_text())
    cases = next(ast.literal_eval(n.value) for n in tree.body
                 if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "CASES" for t in n.targets))
    require(len(cases) == 16, "Sixteen cases")
    for name in cases:
        require((ROOT / "independent_cases" / name).is_file(), "Missing case")
    require(len(list((ROOT / "independent_cases/egrr_copies").glob("*.py"))) == 7,
            "Seven EGRR scan inputs")
    for name in ("vl002_docstring.py", "empty_pytest.py", "verify_unreachable_raise.py"):
        require((ROOT / "independent_evidence/reproductions" / name).is_file(), name)
    require((ROOT / "independent_cases/empty").is_dir(), "Empty input directory")
    print(f"SHA256SUMS: {len(listed)} file hashes PASS")
    print("Pinned scanner, retained input hashes, 16 cases and 7 EGRR inputs: PASS")
    print("Distribution verification: PASS; no original workspace needed")


if __name__ == "__main__":
    main()

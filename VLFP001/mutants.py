#!/usr/bin/env python3
"""VL-FP-001 F5: remove each new guard in a temporary copy; the new tests must fail for every one."""
from pathlib import Path
import shutil, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTANTS = (
    ("tuple-assert", "        if isinstance(t, ast.Tuple) and t.elts:\n            self.tautological_asserts += 1\n        elif",
                     "        if False:\n            self.tautological_asserts += 1\n        elif"),
    ("swallow", "        swallows = any(self._handler_swallows(h) for h in n.handlers)",
                "        swallows = False"),
    ("uncollected-test", "    return len(s.test_names & s.names_used)", "    return s.test_defs"),
    ("top-level-block-executable", "        for n in tree.body) or any(_runs_a_check(n) for n in tree.body)",
                                   "        for n in tree.body)"),
)
killed = 0
for name, old, new in MUTANTS:
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(ROOT / "tests", Path(tmp) / "tests")
        src = (ROOT / "vacuity_lint.py").read_text(encoding="utf-8")
        assert src.count(old) == 1, name
        (Path(tmp) / "vacuity_lint.py").write_text(src.replace(old, new), encoding="utf-8")
        r = subprocess.run([sys.executable, "-m", "unittest", "tests.test_vlfp001"], cwd=tmp,
                           capture_output=True, text=True)
        ok = r.returncode != 0
        killed += ok
        print(f"mutant {name}: {'KILLED' if ok else 'SURVIVED'} ({r.stderr.strip().splitlines()[-1]})")
print(f"VL-FP-001 MUTANTS: {killed}/{len(MUTANTS)} killed")
sys.exit(0 if killed == len(MUTANTS) else 1)

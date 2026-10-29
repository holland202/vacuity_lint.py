"""E17-B fixtures, as data.

Every constant E17-B shares with E17 is imported from E17/fixtures/fixtures.py, so the shared
bytes are E17's own. The new bases differ from E17's helper bases only in the helper's path and
in the one import line that names it. Same shape as E17's module: LANGUAGES[lang] has "bases"
(path -> content) and "cases" (case -> (base name, overlay)); an overlay value of None deletes
the file.
"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "e17_fixtures", os.path.join(HERE, "..", "E17", "fixtures", "fixtures.py"))
E17 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E17)


def _moved(files, old_path, new_path, old_import, new_import):
    """Copy a base, move one file, and rewrite the one import line in each file that names it."""
    out = {}
    for path, content in files.items():
        if path == old_path:
            out[new_path] = content
            continue
        if old_import in content:
            if content.count(old_import) != 1:
                raise ValueError(f"{path}: expected one import of the helper")
            content = content.replace(old_import, new_import)
        out[path] = content
    if new_path not in out:
        raise ValueError(f"{old_path} not found in the base")
    return out


# ---------------------------------------------------------------- Python

PY_NOOP_HELPER = E17.PY_CASES["H1"][1]["tests/helpers.py"]

PY_BASE_HELPER_ROOT = _moved(E17.PY_BASE_HELPER, "tests/helpers.py", "helpers.py",
                             "from helpers import check_equal", "from helpers import check_equal")
PY_BASE_HELPER_NEAR = _moved(E17.PY_BASE_HELPER, "tests/helpers.py", "tests_support/helpers.py",
                             "from helpers import check_equal",
                             "from tests_support.helpers import check_equal")

PY_C0 = E17.PY_CASES["C0"][1]
PY_C2 = E17.PY_CASES["C2"][1]

PY_CASES = {
    "H1": E17.PY_CASES["H1"],
    "C0-h": ("base_helper", PY_C0),
    "C2-h": ("base_helper", PY_C2),
    "H1-root": ("base_helper_root", {"calc.py": E17.PY_CALC_BROKEN, "helpers.py": PY_NOOP_HELPER}),
    "C0-root": ("base_helper_root", PY_C0),
    "C2-root": ("base_helper_root", PY_C2),
    "H1-near": ("base_helper_near", {"calc.py": E17.PY_CALC_BROKEN,
                                     "tests_support/helpers.py": PY_NOOP_HELPER}),
    "C0-near": ("base_helper_near", PY_C0),
    "C2-near": ("base_helper_near", PY_C2),
}

# ---------------------------------------------------------------- Node

NODE_NOOP_HELPER = E17.NODE_CASES["H1"][1]["assertions.mjs"]

NODE_BASE_HELPER_TESTS = _moved(E17.NODE_BASE_HELPER, "assertions.mjs", "tests/assertions.mjs",
                                'from "./assertions.mjs"', 'from "./tests/assertions.mjs"')

NODE_C0 = E17.NODE_CASES["C0"][1]
NODE_C2 = E17.NODE_CASES["C2"][1]

NODE_CASES = {
    "H1": E17.NODE_CASES["H1"],
    "C0-h": ("base_helper", NODE_C0),
    "C2-h": ("base_helper", NODE_C2),
    "H1-tests": ("base_helper_tests", {"calc.mjs": E17.NODE_CALC_BROKEN,
                                       "tests/assertions.mjs": NODE_NOOP_HELPER}),
    "C0-tests": ("base_helper_tests", NODE_C0),
    "C2-tests": ("base_helper_tests", NODE_C2),
}

LANGUAGES = {
    "node": {"bases": {"base_helper": E17.NODE_BASE_HELPER, "base_helper_tests": NODE_BASE_HELPER_TESTS},
             "cases": NODE_CASES},
    "python": {"bases": {"base_helper": E17.PY_BASE_HELPER, "base_helper_root": PY_BASE_HELPER_ROOT,
                         "base_helper_near": PY_BASE_HELPER_NEAR},
               "cases": PY_CASES},
}

# The two cases E17 already ran, with the patch sha256 E17 recorded for each.
REPLICATIONS = {("python", "H1"), ("node", "H1")}
# The person-look sample registered under C-SYNTH.
PERSON_SAMPLE = [("python", "H1-root"), ("python", "H1-near"), ("node", "H1-tests")]

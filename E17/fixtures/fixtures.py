"""E17 fixtures, as data. The single source for every fixture repository E17 builds.

Each language has bases (a dict of path -> content) and cases. A case names its base and an
overlay: path -> new content, or None to delete the file. build_fixtures.py turns each case into
a git repository at the base commit plus a patch file, exactly as PREREG.md describes.
"""

# ---------------------------------------------------------------- Node

NODE_PKG = '{"name":"calcfx","private":true,"type":"module","scripts":{"test":"node --test"}}\n'
NODE_HEAD = ('import test from "node:test";\n'
             'import assert from "node:assert/strict";\n'
             'import { add } from "./calc.mjs";\n')
NODE_CALC_OK = "export const add = (a, b) => a + b;\n"
NODE_CALC_BROKEN = "export const add = (a, b) => a * b;\n"

NODE_BASE = {
    "package.json": NODE_PKG,
    "calc.mjs": NODE_CALC_OK,
    "calc.test.mjs": NODE_HEAD + 'test("adds", () => { assert.equal(add(2, 3), 5); });\n',
    "zero.test.mjs": NODE_HEAD + 'test("adds zeros", () => { assert.equal(add(0, 0), 0); });\n',
}
NODE_HELPER_HEAD = ('import test from "node:test";\n'
                    'import { checkEqual } from "./assertions.mjs";\n'
                    'import { add } from "./calc.mjs";\n')
NODE_BASE_HELPER = {
    "package.json": NODE_PKG,
    "calc.mjs": NODE_CALC_OK,
    "assertions.mjs": ('import assert from "node:assert/strict";\n'
                       "export function checkEqual(actual, expected) { assert.equal(actual, expected); }\n"),
    "calc.test.mjs": NODE_HELPER_HEAD + 'test("adds", () => { checkEqual(add(2, 3), 5); });\n',
    "zero.test.mjs": NODE_HELPER_HEAD + 'test("adds zeros", () => { checkEqual(add(0, 0), 0); });\n',
}


def node_calc_test(body):
    return NODE_HEAD + body


NODE_CASES = {
    "C0": ("base", {"calc.mjs": "export const add = (a, b) => b + a;\n"}),
    "C1": ("base", {
        "calc.mjs": "export const add = (a, b) => b + a;\n",
        "zero.test.mjs": NODE_HEAD + 'test("adds zero to zero", () => { assert.equal(add(0, 0), 0); });\n',
        "calc.test.mjs": node_calc_test(
            'test("adds", () => { assert.equal(add(2, 3), 5); });\n'
            'test("adds negatives", () => { assert.equal(add(-2, -3), -5); });\n'),
    }),
    "C2": ("base", {"calc.mjs": NODE_CALC_BROKEN}),
    "W1": ("base", {"calc.mjs": NODE_CALC_BROKEN,
                    "calc.test.mjs": node_calc_test(
                        'const adds = () => { assert.equal(add(2, 3), 5); };\n')}),
    "W1p": ("base", {"calc.mjs": NODE_CALC_BROKEN,
                     "calc.test.mjs": node_calc_test(
                         'test.skip("adds", () => { assert.equal(add(2, 3), 5); });\n')}),
    "W2": ("base", {"calc.mjs": NODE_CALC_BROKEN,
                    "calc.test.mjs": node_calc_test(
                        'test("adds", () => { try { assert.equal(add(2, 3), 5); } catch {} });\n')}),
    "W3": ("base", {"calc.mjs": NODE_CALC_BROKEN,
                    "calc.test.mjs": node_calc_test(
                        '// test("adds", () => { assert.equal(add(2, 3), 5); });\n')}),
    "W3d": ("base", {"calc.mjs": NODE_CALC_BROKEN, "calc.test.mjs": None}),
    "W4": ("base", {"calc.mjs": NODE_CALC_BROKEN,
                    "calc.test.mjs": node_calc_test(
                        'test("adds", () => { assert.ok(add(2, 3) > 0); });\n')}),
    "W4b": ("base", {"calc.mjs": NODE_CALC_BROKEN,
                     "calc.test.mjs": node_calc_test(
                         'test("adds", () => { assert.ok(add(2, 3) !== undefined); });\n')}),
    "H1": ("base_helper", {"calc.mjs": NODE_CALC_BROKEN,
                           "assertions.mjs": "export function checkEqual(actual, expected) {}\n"}),
    "K1": ("base", {"calc.mjs": NODE_CALC_BROKEN,
                    "package.json": NODE_PKG.replace('"node --test"',
                                                     '"node --test --test-name-pattern=zero"')}),
    "G1": ("base", {"calc.mjs": "export const add = (a, b) => (a === 2 && b === 3 ? 5 : a * b);\n"}),
}

# ---------------------------------------------------------------- Python

PY_PYPROJECT = '''[project]
name = "calcfx"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.uv]
native-tls = true
'''
PY_CALC_OK = "def add(a, b):\n    return a + b\n"
PY_CALC_BROKEN = "def add(a, b):\n    return a * b\n"
PY_CALC_TEST = "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
PY_ZERO_TEST = "from calc import add\n\n\ndef test_zeros():\n    assert add(0, 0) == 0\n"

PY_BASE = {
    "pyproject.toml": PY_PYPROJECT,
    "calc.py": PY_CALC_OK,
    "tests/test_calc.py": PY_CALC_TEST,
    "tests/test_zero.py": PY_ZERO_TEST,
}
PY_BASE_HELPER = {
    "pyproject.toml": PY_PYPROJECT,
    "calc.py": PY_CALC_OK,
    "tests/helpers.py": "def check_equal(actual, expected):\n    assert actual == expected\n",
    "tests/test_calc.py": ("from calc import add\nfrom helpers import check_equal\n\n\n"
                           "def test_add():\n    check_equal(add(2, 3), 5)\n"),
    "tests/test_zero.py": ("from calc import add\nfrom helpers import check_equal\n\n\n"
                           "def test_zeros():\n    check_equal(add(0, 0), 0)\n"),
}

PY_CASES = {
    "C0": ("base", {"calc.py": "def add(a, b):\n    return b + a\n"}),
    "C1": ("base", {
        "calc.py": "def add(a, b):\n    return b + a\n",
        "tests/test_zero.py": "from calc import add\n\n\ndef test_zeros_stay_zero():\n    assert add(0, 0) == 0\n",
        "tests/test_calc.py": PY_CALC_TEST + "\n\ndef test_add_negatives():\n    assert add(-2, -3) == -5\n",
    }),
    "C2": ("base", {"calc.py": PY_CALC_BROKEN}),
    "W1": ("base", {"calc.py": PY_CALC_BROKEN,
                    "tests/test_calc.py": "from calc import add\n\n\ndef check_add():\n    assert add(2, 3) == 5\n"}),
    "W1p": ("base", {"calc.py": PY_CALC_BROKEN,
                     "tests/test_calc.py": ("import pytest\n\nfrom calc import add\n\n\n"
                                            "@pytest.mark.skip(reason=\"flaky\")\n"
                                            "def test_add():\n    assert add(2, 3) == 5\n")}),
    "W2": ("base", {"calc.py": PY_CALC_BROKEN,
                    "tests/test_calc.py": ("from calc import add\n\n\ndef test_add():\n"
                                           "    try:\n        assert add(2, 3) == 5\n"
                                           "    except AssertionError:\n        pass\n")}),
    "W3": ("base", {"calc.py": PY_CALC_BROKEN,
                    "tests/test_calc.py": ("from calc import add\n\n\n"
                                           "# def test_add():\n#     assert add(2, 3) == 5\n")}),
    "W3d": ("base", {"calc.py": PY_CALC_BROKEN, "tests/test_calc.py": None}),
    "W4": ("base", {"calc.py": PY_CALC_BROKEN,
                    "tests/test_calc.py": "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) > 0\n"}),
    "W4b": ("base", {"calc.py": PY_CALC_BROKEN,
                     "tests/test_calc.py": "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) is not None\n"}),
    "H1": ("base_helper", {"calc.py": PY_CALC_BROKEN,
                           "tests/helpers.py": "def check_equal(actual, expected):\n    pass\n"}),
    "K1": ("base", {"calc.py": PY_CALC_BROKEN,
                    "pyproject.toml": PY_PYPROJECT.replace(
                        'pythonpath = ["."]\n', 'pythonpath = ["."]\naddopts = "-k \'not test_add\'"\n')}),
    "G1": ("base", {"calc.py": "def add(a, b):\n    return 5 if (a, b) == (2, 3) else a * b\n"}),
}

LANGUAGES = {
    "node": {"bases": {"base": NODE_BASE, "base_helper": NODE_BASE_HELPER}, "cases": NODE_CASES},
    "python": {"bases": {"base": PY_BASE, "base_helper": PY_BASE_HELPER}, "cases": PY_CASES},
}
CHEATS = ["W1", "W1p", "W2", "W3", "W3d", "W4", "W4b", "H1", "K1"]
CONTROLS = ["C0", "C1", "C2"]
OUTSIDE = ["G1"]

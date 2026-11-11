"""Build the E18 fixture corpus in a temporary directory at run time.

Nothing here is committed as a test file, so the repository's own CI scan
tree is unchanged. Returns (tempdir, expected_flagged, expected_clean).
Fixture sources deliberately avoid this repository's failure-text trigger
substrings.
"""
import tempfile
from pathlib import Path

FLAGGED = {
    "test_a1_notin.py": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_a1_secret_absent(self):\n"
        "        page = render()\n"
        "        self.assertNotIn('secret-name', page)\n"
    ),
    "test_a2_two_negatives.py": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_a2_no_leak_no_flag(self):\n"
        "        out = run()\n"
        "        self.assertNotEqual(out.status, 'leaked')\n"
        "        self.assertFalse(out.flagged)\n"
    ),
    "test_a3_isnone.py": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_a3_nothing_returned(self):\n"
        "        self.assertIsNone(lookup('ghost'))\n"
    ),
    "test_a4_empty_equal.py": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_a4_no_results(self):\n"
        "        self.assertEqual(scan(), [])\n"
    ),
    "test_a5_plain_asserts.py": (
        "def test_a5_absent():\n"
        "    page = render()\n"
        "    assert 'secret-name' not in page\n"
        "    assert not page.endswith('x')\n"
    ),
    "test_a6_len_zero.py": (
        "def test_a6_zero_findings():\n"
        "    assert len(collect()) == 0\n"
    ),
    "test_a7_asserttrue_not.py": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_a7_nothing_there(self):\n"
        "        self.assertTrue(not present())\n"
    ),
    "test_a8_mock_only.py": (
        "def test_a8_never_called(mocker):\n"
        "    hook = mocker.stub()\n"
        "    run(hook)\n"
        "    hook.assert_not_called()\n"
    ),
}

CLEAN = {
    "test_c1_two_sided.py": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_c1_filter_removes_only_target(self):\n"
        "        page = render()\n"
        "        self.assertIn('public-name', page)\n"
        "        self.assertNotIn('secret-name', page)\n"
    ),
    "test_c2_positive.py": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_c2_value(self):\n"
        "        self.assertEqual(compute(), 'abc')\n"
    ),
    "test_c3_raises.py": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_c3_rejects(self):\n"
        "        with self.assertRaises(ValueError):\n"
        "            parse('bad')\n"
    ),
    "test_c4_no_asserts.py": (
        "def test_c4_out_of_scope():\n"
        "    run()\n"
    ),
    "test_c5_length_positive.py": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_c5_has_rows(self):\n"
        "        self.assertGreater(len(rows()), 0)\n"
    ),
    "test_c6_mixed.py": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_c6_present_and_absent(self):\n"
        "        out = run()\n"
        "        self.assertNotEqual(out, None)\n"
        "        self.assertIn('row', out)\n"
    ),
    "test_c7_helper.py": (
        "def check_nothing(page):\n"
        "    assert 'secret-name' not in page\n"
        "def test_c7_uses_helper():\n"
        "    assert render() == 'body'\n"
    ),
    "test_c8_nonzero_literal.py": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_c8_count_and_guard(self):\n"
        "        self.assertEqual(count(), 5)\n"
        "        self.assertFalse(overflowed())\n"
    ),
}


def build():
    d = Path(tempfile.mkdtemp(prefix="e18-fixtures-"))
    for name, src in {**FLAGGED, **CLEAN}.items():
        (d / name).write_text(src, encoding="utf-8")
    expected_flagged = {
        "test_a1_secret_absent", "test_a2_no_leak_no_flag", "test_a3_nothing_returned",
        "test_a4_no_results", "test_a5_absent", "test_a6_zero_findings",
        "test_a7_nothing_there", "test_a8_never_called",
    }
    expected_clean = {
        "test_c1_filter_removes_only_target", "test_c2_value", "test_c3_rejects",
        "test_c4_out_of_scope", "test_c5_has_rows", "test_c6_present_and_absent",
        "test_c7_uses_helper", "test_c8_count_and_guard",
    }
    return d, expected_flagged, expected_clean

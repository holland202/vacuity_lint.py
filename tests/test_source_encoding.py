"""Source-decoding regressions; fixture bytes are parsed, never executed."""
import codecs
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import vacuity_lint as lint

SCANNER = Path(lint.__file__).resolve()
VALID_ENCODINGS = (
    ("utf8", "", "utf-8"),
    ("utf8-bom", "", "utf-8-sig"),
    ("latin1", "# coding: latin-1\n", "latin-1"),
    ("second-line-cookie", "#!/usr/bin/env python3\n# coding: cp1252\n", "cp1252"),
)
INVALID_SOURCES = (
    ("unknown-codec", b"# coding: imaginary-codec\nvalue = 1\n"),
    ("bom-conflict", codecs.BOM_UTF8 + b"# coding: latin-1\nvalue = 1\n"),
    ("invalid-utf8", b'value = "\xff"\n'),
    ("late-invalid-utf8", b'value = 1\n# comment\ntext = "\xff"\n'),
    ("declared-ascii", b'# coding: ascii\nvalue = "\xe9"\n'),
    ("non-text-codec", b"# coding: base64_codec\nvalue = 1\n"),
    ("late-cookie", b'# comment\n# comment\n# coding: latin-1\nvalue = "\xe9"\n'),
)


class SourceEncodingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vacuity-encoding-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, source, name="verify_encoding.py"):
        target = self.root / name
        target.write_bytes(source)
        return target

    def invoke(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SCANNER), *map(str, arguments)],
            capture_output=True, text=True, timeout=15, check=False,
        )

    def test_valid_encodings_preserve_clean_and_defective_verdicts(self):
        for label, cookie, encoding in VALID_ENCODINGS:
            for body, expected in (
                ("café = 1\nassert café == 1\n", []),
                ("print('[FAIL] café')\n", ["PRINTS_FAIL_ONLY"]),
            ):
                with self.subTest(encoding=label, expected=expected):
                    source = (cookie + body).encode(encoding)
                    compile(source, "fixture.py", "exec")  # validate without executing
                    path = self.write(source)
                    findings, scan = lint.analyse(path)
                    self.assertEqual([code for code, _ in findings], expected)
                    self.assertIsNotNone(scan)

    def test_encoded_comment_preserves_exact_suppression_reason(self):
        source = (
            "# coding: latin-1\n"
            "# vacuity-lint: intentional - café sensor is advisory\n"
            "print('[FAIL] café')\n"
        ).encode("latin-1")
        findings, scan = lint.analyse(self.write(source))
        self.assertEqual(findings, [])
        self.assertIsNotNone(scan)
        self.assertEqual(scan.suppressed, "café sensor is advisory")

    def test_encoded_string_marker_does_not_suppress(self):
        source = (
            "# coding: latin-1\n"
            "marker = '# vacuity-lint: intentional - café example'\n"
            "print('[FAIL] café')\n"
        ).encode("latin-1")
        findings, scan = lint.analyse(self.write(source))
        self.assertEqual([code for code, _ in findings], ["PRINTS_FAIL_ONLY"])
        self.assertIsNone(scan.suppressed)

    def test_invalid_encoding_is_unparseable_in_both_io_modes(self):
        for label, source in INVALID_SOURCES:
            with self.subTest(case=label):
                with self.assertRaises(SyntaxError):
                    compile(source, "fixture.py", "exec")
                path = self.write(source)
                for strict_io in (False, True):
                    with self.subTest(strict_io=strict_io):
                        findings, scan = lint.analyse(path, strict_io=strict_io)
                        self.assertEqual([code for code, _ in findings], ["UNPARSEABLE"])
                        self.assertTrue(findings[0][1])
                        self.assertIsNone(scan)

    def test_invalid_encoding_cli_retains_vl005_contract(self):
        for label, source in INVALID_SOURCES:
            path = self.write(source)
            for output in ("text", "json"):
                with self.subTest(case=label, output=output):
                    result = self.invoke(path, "--format", output)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertEqual(result.stderr, "")
                    if output == "json":
                        data = json.loads(result.stdout)
                        self.assertEqual(data["status"], "findings")
                        self.assertEqual(data["files_scanned"], 1)
                        self.assertEqual(data["coverage_errors"], [])
                        self.assertEqual(data["suppressions"], [])
                        finding, = data["findings"]
                        self.assertEqual(
                            (finding["rule_id"], finding["category"], finding["severity"]),
                            ("VL005", "analysis_error", "error"),
                        )
                    else:
                        self.assertIn("UNPARSEABLE", result.stdout)
                        self.assertNotIn("no vacuous verification found", result.stdout)

    def test_invalid_encoding_cannot_be_suppressed(self):
        source = (
            b"# coding: imaginary-codec\n"
            b"# vacuity-lint: intentional - advisory only\n"
            b"print('[FAIL]')\n"
        )
        result = self.invoke(self.write(source), "--format", "json")
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        self.assertEqual([f["rule_id"] for f in data["findings"]], ["VL005"])
        self.assertEqual(data["suppressions"], [])

    def test_encoding_error_does_not_hide_other_files_or_coverage_errors(self):
        bad = self.write(INVALID_SOURCES[0][1])
        defect = self.write(b"print('[FAIL]')\n", "verify_defect.py")
        missing = self.root / "missing"
        for extra, expected_exit in (((), 1), ((missing,), 2)):
            with self.subTest(extra=extra):
                result = self.invoke(bad, defect, *extra, "--format", "json")
                self.assertEqual(result.returncode, expected_exit)
                data = json.loads(result.stdout)
                self.assertEqual(data["files_scanned"], 2)
                self.assertEqual({f["rule_id"] for f in data["findings"]}, {"VL002", "VL005"})
                self.assertEqual(data["status"], "analysis_error" if extra else "findings")
                self.assertEqual([e["path"] for e in data["coverage_errors"]],
                                 [str(missing)] if extra else [])

    def test_decoding_never_executes_inspected_source(self):
        sentinel = self.root / "executed.txt"
        source = (
            "# coding: latin-1\nfrom pathlib import Path\n"
            f"Path({str(sentinel)!r}).write_text('executed')\n"
            "print('[FAIL] café')\n"
        ).encode("latin-1")
        result = self.invoke(self.write(source), "--format", "json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual([f["rule_id"] for f in json.loads(result.stdout)["findings"]], ["VL002"])
        self.assertFalse(sentinel.exists())


if __name__ == "__main__":
    unittest.main()

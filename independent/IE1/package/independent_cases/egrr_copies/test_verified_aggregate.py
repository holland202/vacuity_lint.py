"""End-to-end constructed tests for payload-verified aggregation."""

from copy import deepcopy
from hashlib import sha256
import unittest

from canonical_evidence import evidence_sha256, export_case_envelope
from case_envelope import (
    REQUIRED_ARM_NAMES,
    SCHEMA_VERSION,
    build_case_envelope,
)
from verified_aggregate import verified_aggregate


def constructed_full_set():
    expected = [f"{index:03d}" for index in range(100)]
    seeds = {case_id: 900 + index for index, case_id in enumerate(expected)}
    records = []
    payloads_by_case = {}

    for case_id in expected:
        arms = {}
        payloads = {}
        for name in sorted(REQUIRED_ARM_NAMES):
            payload = f"constructed:{case_id}:{name}".encode("ascii")
            indices = [] if name == "uncorrected" else list(range(128))
            payloads[name] = payload
            arms[name] = {
                "status": "VALID",
                "error_code": None,
                "serialized_bytes": len(payload),
                "payload_sha256": sha256(payload).hexdigest(),
                "decode_ok": True,
                "correction_count": len(indices),
                "correction_indices": indices,
                "calibration_mse": 0.8,
                "evaluation_mse": 0.8 if name == "covariance" else 1.0,
            }
        identity = {
            "study_id": "EGRR-DESC-001-DRAFT",
            "case_id": case_id,
            "seed": seeds[case_id],
            "generator": "constructed-fixture",
            "draw_order": "constructed-only",
            "source_commit": "a" * 40,
            "environment": {"python": "constructed-test"},
            "input_hashes": {"input": "b" * 64},
        }
        records.append(build_case_envelope(
            identity, arms, payloads, expected_seed=seeds[case_id]
        ))
        payloads_by_case[case_id] = payloads

    digests = {
        record["identity"]["case_id"]: evidence_sha256(
            export_case_envelope(record)
        )
        for record in records
    }
    return records, payloads_by_case, digests, expected, seeds


def refresh_digest(records, digests, index):
    record = records[index]
    digests[record["identity"]["case_id"]] = evidence_sha256(
        export_case_envelope(record)
    )


class VerifiedAggregateTests(unittest.TestCase):
    def run_verified(self, fixture):
        records, payloads, digests, expected, seeds = fixture
        return verified_aggregate(
            records,
            payloads_by_case=payloads,
            evidence_digests_by_case=digests,
            expected_case_ids=expected,
            expected_seeds=seeds,
        )

    def assert_failed_with(self, result, *codes):
        self.assertIsNone(result["full_set_mean"])
        observed = {item["code"] for item in result["failure_manifest"]}
        for code in codes:
            self.assertIn(code, observed)

    def test_valid_100_case_payload_set(self):
        fixture = constructed_full_set()
        originals = deepcopy(fixture[:3])
        result = self.run_verified(fixture)
        self.assertEqual(result["run_status"], "VALID")
        self.assertAlmostEqual(result["full_set_mean"], 0.2)
        self.assertEqual(fixture[:3], originals)

    def test_serialization_and_set_sabotage_scenarios(self):
        scenarios = {}

        fixture = constructed_full_set()
        fixture[1]["010"]["random"] += b"corrupt"
        scenarios["corrupted payload"] = (fixture, "PAYLOAD_HASH_MISMATCH")

        fixture = constructed_full_set()
        del fixture[1]["010"]
        scenarios["missing payload set"] = (fixture, "MISSING_CASE_PAYLOADS")

        fixture = constructed_full_set()
        fixture[2]["010"] = "0" * 64
        scenarios["digest mismatch"] = (fixture, "EVIDENCE_DIGEST_MISMATCH")

        fixture = constructed_full_set()
        fixture[0][10]["arms"]["random"]["serialized_bytes"] += 1
        refresh_digest(fixture[0], fixture[2], 10)
        scenarios["byte count mismatch"] = (
            fixture, "SERIALIZED_BYTE_COUNT_MISMATCH"
        )

        fixture = constructed_full_set()
        fixture[0].append(deepcopy(fixture[0][10]))
        scenarios["duplicate case"] = (fixture, "DUPLICATE_CASE")

        fixture = constructed_full_set()
        fixture[0][10]["identity"]["seed"] += 1
        refresh_digest(fixture[0], fixture[2], 10)
        scenarios["wrong seed"] = (
            fixture, "VERIFIED_CASE_IDENTITY_MISMATCH"
        )

        fixture = constructed_full_set()
        del fixture[0][10]["arms"]["random"]
        scenarios["missing arm"] = (fixture, "MISSING_ARM_OR_PAYLOAD")

        fixture = constructed_full_set()
        fixture[0][10]["arms"]["random"]["correction_indices"] = [0] * 128
        scenarios["invalid corrections"] = (
            fixture, "VERIFIED_SIX_ARM_EVIDENCE_FAILED"
        )

        for label, (fixture, code) in scenarios.items():
            with self.subTest(label=label):
                self.assert_failed_with(self.run_verified(fixture), code)

    def test_numeric_status_and_provenance_sabotage_scenarios(self):
        fixture = constructed_full_set()
        case = fixture[0][10]
        case["arms"]["random"]["evaluation_mse"] = float("nan")
        case["arms"]["random"]["status"] = "INVALID_NUMERIC"
        case["arms"]["random"]["error_code"] = "INVALID_MSE"
        case["errors"] = [{
            "stage": "arms", "arm": "random", "code": "INVALID_MSE",
            "status": "INVALID_NUMERIC",
        }]
        case["case_status"] = "INVALID_NUMERIC"
        result = self.run_verified(fixture)
        self.assert_failed_with(result, "INVALID_MSE")

        fixture = constructed_full_set()
        case = fixture[0][10]
        case["arms"]["random"]["decode_ok"] = False
        result = self.run_verified(fixture)
        self.assert_failed_with(result, "DECODE_FAILURE")

        for covariance, magnitude, false_pair, expected_code in (
            (0.5, 0.0, None, "ZERO_DENOMINATOR"),
            (1e308, 1e-308, None, "RATIO_NONFINITE"),
            (0.8, 1.0, {"status": "VALID", "r": 0.7},
             "PAIRED_RATIO_MISMATCH"),
        ):
            fixture = constructed_full_set()
            case = fixture[0][10]
            case["arms"]["covariance"]["evaluation_mse"] = covariance
            case["arms"]["magnitude"]["evaluation_mse"] = magnitude
            rebuilt = build_case_envelope(
                case["identity"], case["arms"], fixture[1]["010"],
                expected_seed=fixture[4]["010"],
            )
            fixture[0][10] = rebuilt
            if false_pair is not None:
                fixture[0][10]["pair"].update(false_pair)
            refresh_digest(fixture[0], fixture[2], 10)
            with self.subTest(code=expected_code):
                self.assert_failed_with(
                    self.run_verified(fixture), expected_code
                )

        fixture = constructed_full_set()
        del fixture[0][10]["identity"]["environment"]
        result = self.run_verified(fixture)
        self.assert_failed_with(result, "INVALID_CASE_IDENTITY")

    def test_two_independent_failures_are_both_retained(self):
        fixture = constructed_full_set()
        fixture[1]["010"]["random"] += b"corrupt"
        fixture[0][20]["identity"]["seed"] += 1
        refresh_digest(fixture[0], fixture[2], 20)
        result = self.run_verified(fixture)
        self.assert_failed_with(
            result, "PAYLOAD_HASH_MISMATCH",
            "VERIFIED_CASE_IDENTITY_MISMATCH",
        )

    def test_invalid_registration_inputs_fail_closed(self):
        invalid_registrations = (
            (None, None),
            ("000", "not-a-mapping"),
            ({"000": 900}, {"000": 900}),
            ([f"{index:03d}" for index in range(99)],
             {f"{index:03d}": 900 + index for index in range(99)}),
            ([f"{index:03d}" for index in range(100)],
             {f"{index:03d}": 900 + index for index in range(99)}),
            ([f"{index:03d}" for index in range(100)],
             {**{f"{index:03d}": 900 + index for index in range(100)},
              "100": 1000}),
            ([f"{index:03d}" for index in range(100)],
             {**{f"{index:03d}": 900 + index for index in range(100)},
              "050": "not-an-integer"}),
            ([*range(100)], {index: 900 + index for index in range(100)}),
        )
        for expected, seeds in invalid_registrations:
            fixture = constructed_full_set()
            with self.subTest(expected=expected, seeds_type=type(seeds)):
                result = verified_aggregate(
                    fixture[0], payloads_by_case=fixture[1],
                    evidence_digests_by_case=fixture[2],
                    expected_case_ids=expected, expected_seeds=seeds,
                )
                self.assertEqual(result["run_status"], "INSTRUMENT_FAILED")
                self.assert_failed_with(result, "INVALID_FIXED_REGISTRATION")

    def test_invalid_top_level_containers_fail_closed(self):
        fixture = constructed_full_set()
        for field, value, code in (
            ("records", None, "INVALID_RECORD_CONTAINER"),
            ("records", "records", "INVALID_RECORD_CONTAINER"),
            ("payloads", None, "INVALID_PAYLOAD_CONTAINER"),
            ("payloads", "payloads", "INVALID_PAYLOAD_CONTAINER"),
            ("digests", None, "INVALID_EVIDENCE_DIGEST_CONTAINER"),
            ("digests", "digests", "INVALID_EVIDENCE_DIGEST_CONTAINER"),
        ):
            records, payloads, digests, expected, seeds = fixture
            arguments = {
                "records": records, "payloads": payloads, "digests": digests,
            }
            arguments[field] = value
            with self.subTest(field=field, value=value):
                result = verified_aggregate(
                    arguments["records"], payloads_by_case=arguments["payloads"],
                    evidence_digests_by_case=arguments["digests"],
                    expected_case_ids=expected, expected_seeds=seeds,
                )
                self.assertEqual(result["run_status"], "INSTRUMENT_FAILED")
                self.assert_failed_with(result, code)

    def test_malformed_records_and_non_string_ids_fail_closed(self):
        malformed = (None, "record", {}, {"identity": None},
                     {"identity": {"case_id": {"unhashable": True}}})
        for record in malformed:
            fixture = constructed_full_set()
            fixture[0][0] = record
            with self.subTest(record=record):
                result = self.run_verified(fixture)
                self.assertEqual(result["run_status"], "INSTRUMENT_FAILED")
                self.assert_failed_with(result, "VERIFIED_CASE_SET_MISMATCH")

    def test_seed_identity_mismatch_is_structured_and_ordered(self):
        fixture = constructed_full_set()
        fixture[0][20]["identity"]["seed"] += 1
        fixture[0][3]["identity"]["seed"] += 1
        for index in (20, 3):
            refresh_digest(fixture[0], fixture[2], index)
        result = self.run_verified(fixture)
        mismatches = [
            item["case_id"] for item in result["failure_manifest"]
            if item["code"] == "VERIFIED_CASE_IDENTITY_MISMATCH"
        ]
        self.assertEqual(mismatches, ["003", "020"])


if __name__ == "__main__":
    unittest.main()

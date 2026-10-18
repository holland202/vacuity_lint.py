"""Small constructed EGR2 serializer/decoder integration tests."""

from hashlib import sha256
import struct
import unittest
import zlib

import numpy as np

from egrr import quantize_symmetric, reconstruct
from storage import HEADER, HEADER_SIZE, deserialize, serialize


class EGR2IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.weights = np.array([
            [0.25, -0.75, 1.5, -1.0],
            [0.5, 1.0, -0.25, -1.5],
        ], dtype=np.float64)
        self.quantized = quantize_symmetric(self.weights, 3)

    def round_trip(self, indices, residuals):
        payload = serialize(self.quantized, indices, residuals)
        decoded = deserialize(payload)
        return payload, decoded

    def test_corrected_and_uncorrected_round_trip_bytes_and_sha256(self):
        fixtures = (
            (np.array([], dtype=np.int64), np.array([], dtype=np.float64),
             "125e4edc06c33d87f87ae7956e13bf397c2916dc533a1f9380a0f052e059ee1a"),
            (np.array([1, 6], dtype=np.int64),
             np.array([0.1, -0.3333], dtype=np.float64),
             "99c775222e3da23ac8a29d5a31a0a079b7c113aa7d46e22f08c2106b67320aec"),
        )
        packed_length = (
            self.quantized.values.size * self.quantized.bits + 7
        ) // 8
        for indices, residuals, expected_sha256 in fixtures:
            with self.subTest(k=len(indices)):
                payload, (decoded_q, decoded_indices, decoded_residuals) = (
                    self.round_trip(indices, residuals)
                )
                expected_bytes = HEADER_SIZE + packed_length + len(indices) * 4 + 4
                self.assertEqual(len(payload), expected_bytes)
                self.assertEqual(sha256(payload).hexdigest(), expected_sha256)
                np.testing.assert_array_equal(decoded_q.values,
                                              self.quantized.values)
                np.testing.assert_array_equal(decoded_indices, indices)
                np.testing.assert_array_equal(
                    decoded_residuals,
                    residuals.astype("<f2").astype(np.float64),
                )
                np.testing.assert_array_equal(
                    reconstruct(decoded_q, decoded_indices, decoded_residuals),
                    reconstruct(
                        self.quantized, indices,
                        residuals.astype("<f2").astype(np.float64),
                    ),
                )

    def test_crc_corruption_is_rejected_by_real_decoder(self):
        payload, _ = self.round_trip(
            np.array([1], dtype=np.int64), np.array([0.1])
        )
        corrupted = bytearray(payload)
        corrupted[HEADER_SIZE] ^= 1
        with self.assertRaisesRegex(ValueError, "CRC32 checksum mismatch"):
            deserialize(bytes(corrupted))

    def test_incorrect_k_duplicate_and_out_of_range_indices_are_rejected(self):
        payload, _ = self.round_trip(
            np.array([1, 6], dtype=np.int64), np.array([0.1, -0.2])
        )

        wrong_k = bytearray(payload)
        header = list(struct.unpack(HEADER, wrong_k[:HEADER_SIZE]))
        header[-1] = 3
        wrong_k[:HEADER_SIZE] = struct.pack(HEADER, *header)
        wrong_k[-4:] = struct.pack("<I", zlib.crc32(wrong_k[:-4]))
        with self.assertRaisesRegex(ValueError, "payload length mismatch"):
            deserialize(bytes(wrong_k))

        for label, forged_indices in (
            ("duplicate", (1, 1)),
            ("out-of-range", (1, self.quantized.values.size)),
        ):
            forged = bytearray(payload)
            packed_length = (
                self.quantized.values.size * self.quantized.bits + 7
            ) // 8
            offset = HEADER_SIZE + packed_length
            forged[offset:offset + 4] = struct.pack("<2H", *forged_indices)
            forged[-4:] = struct.pack("<I", zlib.crc32(forged[:-4]))
            with self.subTest(label=label), self.assertRaisesRegex(
                ValueError, "corrupt correction indices"
            ):
                deserialize(bytes(forged))

    def test_serializer_rejects_shape_errors(self):
        with self.assertRaisesRegex(ValueError, "2D weights required"):
            invalid_q = type(self.quantized)(
                self.quantized.values.reshape(-1),
                self.quantized.scale,
                self.quantized.bits,
            )
            serialize(invalid_q, [], [])
        with self.assertRaisesRegex(ValueError, "invalid corrections"):
            serialize(self.quantized, [[1]], [0.1])
        with self.assertRaisesRegex(ValueError, "invalid corrections"):
            serialize(self.quantized, [1], [0.1, 0.2])


if __name__ == "__main__":
    unittest.main()

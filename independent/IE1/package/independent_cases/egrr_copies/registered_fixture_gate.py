"""Constructed 64x32, K=128 EGR2 gate for W2 predictions P1-P3.

This fixture uses seed 901, not either reserved research seed block.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np


EGRR_DIR = Path(__file__).resolve().parents[2] / "experiments" / "egrr_issue28"
sys.path.insert(0, str(EGRR_DIR))

from egrr import quantize_symmetric, reconstruct, select_corrections
from storage import HEADER_SIZE, deserialize, serialize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sabotage", action="store_true")
    args = parser.parse_args()

    rng = np.random.default_rng(901)
    weights = rng.normal(size=(64, 32))
    quantized = quantize_symmetric(weights, 3)
    indices, residuals = select_corrections(
        weights, quantized, 128, "magnitude"
    )
    payload = bytearray(serialize(quantized, indices, residuals))

    if len(payload) != 1311:
        print("GATE: FAIL — registered payload byte count mismatch")
        return 1

    if args.sabotage:
        payload[HEADER_SIZE] ^= 1

    try:
        decoded_q, decoded_indices, decoded_residuals = deserialize(bytes(payload))
    except ValueError as exc:
        if args.sabotage and str(exc) == "CRC32 checksum mismatch":
            print("GATE: FAIL — planted CRC corruption detected")
            return 1
        print(f"GATE: FAIL — unexpected decoder error: {exc}")
        return 2

    if args.sabotage:
        print("GATE: FAIL — planted CRC corruption accepted")
        return 2

    expected = reconstruct(
        quantized,
        indices,
        residuals.astype("<f2").astype(np.float64),
    )
    actual = reconstruct(decoded_q, decoded_indices, decoded_residuals)
    if not np.array_equal(expected, actual):
        print("GATE: FAIL — float16 reconstruction mismatch")
        return 2

    result = {
        "correction_count": int(len(decoded_indices)),
        "payload_bytes": len(payload),
        "payload_sha256": sha256(payload).hexdigest(),
        "shape": [64, 32],
    }
    print("GATE: PASS — registered constructed payload " + json.dumps(
        result, sort_keys=True, separators=(",", ":")
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

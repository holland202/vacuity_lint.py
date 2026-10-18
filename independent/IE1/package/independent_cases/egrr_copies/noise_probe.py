"""Same-input constructed C-NOISE probe; no registered seeds are used."""

from hashlib import sha256
import json
from pathlib import Path
import struct
import sys

import numpy as np


EGRR_DIR = Path(__file__).resolve().parents[2] / "experiments" / "egrr_issue28"
sys.path.insert(0, str(EGRR_DIR))

from egrr import quantize_symmetric, reconstruct, select_corrections
from storage import deserialize, serialize


def main():
    rng = np.random.default_rng(902)
    weights = rng.normal(size=(64, 32))
    inputs = rng.normal(size=(32, 64))
    quantized = quantize_symmetric(weights, 3)
    indices, residuals = select_corrections(
        weights, quantized, 128, "magnitude"
    )
    payload = serialize(quantized, indices, residuals)
    decoded_q, decoded_indices, decoded_residuals = deserialize(payload)
    reconstructed = reconstruct(
        decoded_q, decoded_indices, decoded_residuals
    )
    mse = float(np.mean((inputs @ (weights - reconstructed)) ** 2))
    result = {
        "fixture": "constructed-noise-902",
        "mse_f64_be_hex": struct.pack(">d", mse).hex(),
        "payload_sha256": sha256(payload).hexdigest(),
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

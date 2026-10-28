#!/usr/bin/env python3
"""Compare a reproduction's results.json against the committed one.

Usage: python compare_results.py E15/run/output/results.json YOUR_OUT/results.json

Every non-float value must match exactly: verdicts, counts, the full sorted
per-arm values, unavailable/coverage/bench counts, split counts.
Every float must match to 4 decimal places: p-values, medians, quartiles,
interval ends and rates (the last digits can move between numpy/scipy versions).
Exit 0 = reproduced, 1 = differs, 2 = usage error.
"""
import json
import sys


def walk(a, b, path, diffs):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                diffs.append(f"{path}/{k}: present in only one file")
                continue
            walk(a[k], b[k], f"{path}/{k}", diffs)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append(f"{path}: committed {a} vs yours {b}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", diffs)
        return
    if isinstance(a, float) or isinstance(b, float):
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float))
                and round(a, 4) == round(b, 4)):
            diffs.append(f"{path}: committed {a} vs yours {b}")
        return
    if a != b:
        diffs.append(f"{path}: committed {a} vs yours {b}")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    committed, yours = (json.load(open(p)) for p in sys.argv[1:])
    diffs = []
    walk(committed, yours, "", diffs)
    if diffs:
        print(f"DIFFERS in {len(diffs)} place(s):")
        print("\n".join(diffs[:50]))
        return 1
    print("REPRODUCED: every verdict and count matches; p-values and intervals match to 4 decimals")
    return 0


if __name__ == "__main__":
    sys.exit(main())

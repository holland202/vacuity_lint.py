"""Constructed tests for the verification wrapper's sabotage oracle."""

import sys

from termux_verify import run_check


def test_unrelated_exit_one_does_not_satisfy_crc_sabotage(tmp_path):
    result = run_check(
        "unrelated_exception",
        [sys.executable, "-c", "raise RuntimeError('unrelated')"],
        tmp_path,
        1,
        tmp_path,
        expected_stdout="GATE: FAIL — planted CRC corruption detected\n",
    )
    assert result["actual_exit"] == 1
    assert result["conditions"]["exit_matches"] is True
    assert result["conditions"]["stdout_matches"] is False
    assert result["conditions"]["stderr_matches"] is False
    assert result["passed"] is False

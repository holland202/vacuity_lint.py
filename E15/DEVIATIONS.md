# E15 instrument-freeze deviation — 2026-10-21

Status: **REGISTERED, NOT RUN; instrument decision unresolved.**

The original [PREREG.md](PREREG.md) is unchanged. It pins the scanner at
`e549dbfe9d8c0a03399bef45b66edf7bb6552f58` and prohibits modifying the
instrument before publication of E15 results.

[Issue #7](https://github.com/holland202/vacuity_lint.py/issues/7), opened
2026-10-16, identified that the later v1.1.0 release
`92e1ced2db1c830e2779d108b4042813227130ec` changed the scanner while E15
remained unexecuted. This is a deviation from the literal freeze clause.
It is not resolved by changing the registration retrospectively.

The current Issue #7 repairs create a distinct development instrument
(`2.0.1.dev0`, identified by its own source commit/blob). They do not
replace the E15 pin, alter predictions or sampling rules, authorize E15
selection/scanning, or create an E15 result. No E15 experiment was run for
these engineering corrections.

Before any E15 execution, Chad must separately decide whether to retain
the exact original instrument or approve a new registration. Any later
decision and its rationale must be recorded without rewriting the
original registration or this deviation.

Provenance: ChatGPT (OpenAI, GPT-6) documented the source/history check at
Chad Holland's direction. This note is an engineering record, not
independent scientific validation or a new protocol approval.


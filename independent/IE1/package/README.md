# Vacuity Lint v2.0.0 — Independent Evidence

**Prepared for Chad Holland by Putluru Sandeep (`sunny-kavixo`).**

Start with **[MAINTAINER_HANDOFF.md](MAINTAINER_HANDOFF.md)** for the minimal
VL002 docstring and empty pytest examples, exact commands, expected/observed
results, versions and known limitations.

This is a sanitized distribution of the completed local evidence package. No
upload or submission has been made. The original evidence remains unchanged.
See **[DISTRIBUTION_NOTES.md](DISTRIBUTION_NOTES.md)** for redactions, exclusions
and the distinction between retained evidence and packaging checks.

## Verify after extracting

Open a terminal in this extracted folder:

```bash
shasum -a 256 -c SHA256SUMS
python3 -B verify_package.py
```

Python 3.10+ is required. Verification is offline and does not access the
original workspace, run the scanner or execute any research scripts.

## Contents

- `MAINTAINER_HANDOFF.md`: authoritative handoff and portable reproduction steps.
- `independent_evidence/`: historical report, assembled command/result record,
  environment versions, and three byte-identical minimal reproduction scripts.
  Local paths in historical documents have been redacted and labeled.
- `independent_cases/`: 16 original constructed fixtures, their original driver,
  seven copied EGRR static-scan inputs and the empty input directory.
- `source_snapshot/`: 19 selected unmodified upstream files from
  `da5fe76ddcd660c2d21a89853623e905a0b33708`, including the scanner, rule reference,
  tests, relevant context and original license notices. This is a source subset,
  not a complete checkout or a new release.
- `provenance/`: sanitized content inventory, public issue snapshot and the
  previously recovered EGRR input's source/hash record.
- `SHA256SUMS`: distribution-only integrity manifest; excludes only itself.

The scanner has no third-party runtime dependencies. Only the separate pytest
control needs pytest (recorded version: 9.1.1). No installation is required to
scan the bundled files. Do not run pytest across the whole package: some
constructed fixtures are intentionally defective. **Never execute the copied
EGRR scripts**; they are static inputs and do not form an independent EGRR suite.

VL002 is documented to count docstrings; its diagnostic does not prove the
failure text was emitted. An empty pytest test passing is distinct from a clean
scanner result. The unreachable-path control is a previously documented limit.
No clean scan establishes correctness, security, or scientific validation.

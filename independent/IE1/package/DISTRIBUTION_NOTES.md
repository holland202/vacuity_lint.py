# Distribution notes and privacy review

**Prepared:** 2026-10-18 · **State:** local ZIP only; not uploaded or sent.

## Evidence provenance

The original package's **82 manifest entries all verified** before packaging.
The original `SHA256SUMS` SHA-256 was:

```text
9a90768e5d5038bd3b737abfecff8b74adcb13fc32a3fa09e89af870e8998562
```

The source package is preserved unchanged. This ZIP is a separate, sanitized
distribution and has its own `SHA256SUMS`. Do not compare the ZIP's sanitized
documents against the original manifest. The portable verifier and
`provenance/distribution_inventory.json` verify the distribution and retain
original hashes for copied inputs and the pinned source subset.

The 16 constructed fixtures, their driver, three minimal reproduction scripts,
seven EGRR scan inputs and all 19 bundled upstream source files
are byte-identical to their verified source-package counterparts. Only selected
documentation and packaging metadata were rewritten or redacted. No upstream
code, experimental result value, expected rule, or exit status was changed.

## Redactions and exclusions

- Redacted local home/account paths, temporary workspace identifiers and private
  archive references from the historical report/transcript/environment file.
  Redactions use explicit placeholders; the handoff provides runnable relative
  paths instead. A banner marks the historical documents as sanitized copies.
- Omitted the private origin-to-backup path inventory and original local
  verification record. The new inventory lists only package-relative paths,
  original/distribution hashes, changes and reasons for exclusions.
- Omitted the internal message draft and one-time backup/recovery helpers.
- Omitted unrelated upstream E15 material, E16 execution fixtures and raw
  experiment logs, and CI-only files. These were public upstream context, not
  Sandeep's independent evidence. E16's public results summary is retained for
  the known-limitation reference, explicitly attributed to upstream.
- Replaced the original local-only verifier with a distribution verifier that
  does not need the original backup paths or a full upstream checkout.
- No Git history/configuration, venv, private session log/database, credentials,
  model, cache, Finder metadata or unrelated private research tree is included.

Exact omitted filenames and reasons appear in
`provenance/distribution_inventory.json`. Public professional attribution,
GitHub repository names and original copyright/license notices are intentionally
retained; these are not local account identifiers or credentials.

## Review scope

All original package files were inspected with bounded checks for key/token
formats, credential-bearing URLs, email addresses, local-account paths, private
session references and sensitive filenames. No credential material or personal
email addresses were detected. The final distribution is checked again for
these patterns and for unwanted filesystem/ZIP metadata. Such inspection is not
a general guarantee that an automated detector can recognize every possible
secret.

## Validation scope

The original 20/20 self-tests, 24 regressions, 13 release checks and 16/16
expected classifications remain retained historical results. They are not
relabelled as newly executed packaging tests. After ZIP creation, archive CRCs,
extraction, distribution hashes and a bounded set of portable reproduction
commands are validated in a fresh temporary extraction. Full regression,
release and scientific experiments need not be rerun to package the evidence.

The historical command/result record is assembled, not a complete set of
separate raw stdout/stderr files. Its qualifications remain in the handoff.
The recovered seventh EGRR file is included with its pinned source/hash record;
its recovery must not be confused with a fresh historical scan.

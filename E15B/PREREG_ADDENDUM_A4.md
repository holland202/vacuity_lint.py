# E15-B registration addendum: the SWAY Amendment 4 rows

Status: **REGISTERED, NOT RUN.** Committed after [PREREG.md](PREREG.md) (`2006ee7`) and before any July commit is resolved or any repository is scanned. It adds to PREREG.md. It does not change it.

## Why this file exists

SWAY Amendment 4 (`METHOD_SWAY_AMENDMENT_4.md` in `holland202/principia-artificialis`, adopted when PR #95 merged on 2026-10-24) adds four trigger rows that a registration must answer: C-PRIVATE, C-DESIGN, C-HOLDOUT and C-SYNTH. PREREG.md as committed at `2006ee7` answered none of them. That is a registration error by its author. It is recorded here instead of being fixed by editing PREREG.md.

## The four rows

| Row | Triggered? | Answer |
|---|---|---|
| C-PRIVATE | No | The inputs are the owner's own public repositories. The run records repository names, commit hashes and per-repository counts. It records no author names, email addresses, file contents or per-file paths, and publishes nothing beyond those per-repository records. |
| C-DESIGN | Yes | The readings (R) and (N) explain a difference, so the claim goes beyond "this code gives this output". **Design:** an observational re-measurement of one population at an earlier date, compared with a historical figure. **Strongest claim it supports:** descriptive, namely what the pinned instrument reports on the July code. The (R) and (N) readings are bounded by PREREG.md's classification table. Claims about why the repositories changed, about authorship, or about AI-written code are out of scope. |
| C-HOLDOUT | Yes, partly | **Deciding data:** the classification bands, set from the historical figures 1.2 and about 2.2 (note052) before any July count exists. **Judging data:** the July scan. These are separate. **In-sample part:** the instrument itself was developed against this population (E15 v2 [PREREG_v2.md](../E15/PREREG_v2.md), Limitation 1). With respect to the instrument, the result is in-sample. That cannot be removed, so it is reported as a limitation rather than corrected. |
| C-SYNTH | No | No generated or synthetic inputs. Real repositories at recorded commits. |

## Provenance

Written by Claude (Anthropic, Claude Opus 5.5) on 2026-10-29, after the owner delegated the session's path to Claude. Nothing had been resolved or scanned. Not reviewed line by line by Chad.

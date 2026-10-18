# Vacuity Lint v2.0.0 — licensing transition

## Scope

This is a **license/version change**, not an assertion of additional scanner features or security validation. The same AST-based scanner limitations remain.

- v2.0.0 and later: BSL 1.1, subject to the [LICENSE](LICENSE) and [COMMERCIAL.md](COMMERCIAL.md) terms.
- v1.1.0 and earlier: MIT, archived unchanged at their historical tags (see [ARCHIVED_RELEASES.md](ARCHIVED_RELEASES.md)).
- Each v2.x release changes to Apache License 2.0 four years after its own first publication under the terms in LICENSE.
- New project metadata, CLI version, JSON version, docs example, test assertions, and installed-package smoke checks agree on **2.0.0**.
- No source-code security or functionality changes intended beyond version constants; no automatic PyPI upload.

## Acceptance checks before publication

1. Confirm old tag targets remain at `6ee06713a689507ffd3add814e1ee15f9ef25046` and `92e1ced2db1c830e2779d108b4042813227130ec`.
2. Confirm BSL 1.1 license and MIT historical copy are included in source distribution and wheel, with `BUSL-1.1` packaging metadata.
3. Check `python3 vacuity_lint.py --selftest`, `python3 -m unittest discover -s tests -v`, and package-and-smoke CI for Python 3.10, 3.11, 3.13, and 3.14.
4. Verify CI after merging at the exact main commit, before creating any new tag.
5. Create `v2.0.0` tag at the verified main commit and publish a GitHub Release containing the licensing change and unchanged-scanner limitations.
6. Verify the new release/tag links and record its published-at timestamp. Do not claim v2.0.0 is published before this step.

## GitHub Release notes (proposed)

**Vacuity Lint v2.0.0 — Business Source License transition**

This release changes the licensing terms for v2.0.0 and subsequent versions to **Business Source License 1.1**. Older releases (v1.0.0 and v1.1.0) remain available under their original MIT terms.

Non-production uses such as evaluation and research remain free; the Additional Use Grant also allows defined categories of production use. Organizations not covered by that grant require a separate commercial license for production use. See [LICENSE](LICENSE) for exact conditions and [COMMERCIAL.md](COMMERCIAL.md) for inquiries. Each version converts to Apache-2.0 four years after its own first publication (subject to the LICENSE terms).

**No new detection claims:** this remains a Python AST heuristic that finds certain missing failure paths; it does not prove tests correct or catch every unreachable failing branch.

**Release status: not published until the version tag and GitHub Release are verified.**

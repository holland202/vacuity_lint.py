# Vacuity Lint v2.0.0 — Business Source License transition

Vacuity Lint v2.0.0 changes the license for this and subsequent versions to **Business Source License 1.1 (BSL 1.1)**. This is a **licensing/version release**, not a new scanner feature release.

The historical [v1.0.0](https://github.com/holland202/vacuity_lint.py/releases/tag/v1.0.0) and [v1.1.0](https://github.com/holland202/vacuity_lint.py/releases/tag/v1.1.0) releases remain unchanged under MIT. Those source tags and archives are preserved in [ARCHIVED_RELEASES.md](https://github.com/holland202/vacuity_lint.py/blob/main/ARCHIVED_RELEASES.md).

## New license

- Testing and evaluating Vacuity Lint, research, independent security review, and other non-production use remain free.
- Production use is free under the Additional Use Grant for individuals, nonprofits, academic/research institutions, and qualifying small organizations.
- Larger organizations outside the Additional Use Grant need a separate commercial license for routine business production use, including ongoing CI and code-analysis workflows, or integration into products/services.
- **Each BSL-covered version converts to Apache-2.0 after four years from its first publication**, subject to the exact terms.

The precise conditions and definitions are in [LICENSE](https://github.com/holland202/vacuity_lint.py/blob/main/LICENSE). See [COMMERCIAL.md](https://github.com/holland202/vacuity_lint.py/blob/main/COMMERCIAL.md) for commercial inquiries.

## Functionality and limitations

Scanner rules, JSON diagnostics, and exit-code meanings remain as previously described: 0 = clean scan, 1 = detected findings, 2 = no Python files scanned. The Python AST scanner uses heuristics and does not prove tests are correct or catch every logically unreachable failure path.

The original MIT license text remains available as LICENSE-MIT. This release does not change earlier MIT grants.

No PyPI publication is implied by this GitHub Release.

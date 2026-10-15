# Vacuity Lint v1.1.0 — Final feature release checklist

**Scope is frozen:** a single versioned feature release combining previously
measured exit/entry-point precision corrections and JSON diagnostics. The
published `v1.0.0` GitHub tag and source archive are not modified.

## Included
- Source and package metadata both use `1.1.0`; installed `--version` reports it.
- Existing text output and exit codes **0 clean / 1 finding / 2 no Python files**
  remain the defaults.
- `--format json` reports a documented, stable file-level schema, rule IDs
  VL001–VL005, category/severity labels, and visible reason-bearing suppressions.
- AST-based `__main__` detection, `SystemExit`/exit classification corrections,
  and `ALWAYS_EXITS_ZERO` reachability fix (initially evaluated in PR #4).
- `RULES.md` contains each rule's exact trigger, examples, known blind spots,
  and regression evidence. The README provides quick-start commands.

## Explicit exclusions
- No general dead-branch or Type-B proof; no `assert True` reachability analysis.
- No parallel scanning, file cache, repository-wide suppressions, custom config,
  SARIF, or `--fail-on` flag.
- No PyPI publishing yet; that requires separately establishing the package name,
  owner configuration and trusted-publisher identity.
- No claim that heuristic findings prove a particular file is incorrect.
- No claim that these synthetic regression tests measure real-world precision.

## Evidence required before a v1.1.0 tag and GitHub release
1. Verify exact PR head and **20/20 original self-tests**.
2. Verify the **13 exit/entry-point regression tests** plus **11 JSON CLI tests**
   pass (24 targeted cases) in the same workflow as the planted-defect gate.
3. Verify built **wheel and sdist** install and pass `release_smoke.py`
   (13 installed acceptance checks) on Python 3.10, 3.11, 3.13, 3.14.
4. Verify final `main` merge commit and **post-merge** CI before creating tag.
5. Create **annotated or lightweight** `v1.1.0` tag targeting *that verified
   commit*, not the earlier branch head; confirm tag SHA and release assets.
6. Publish GitHub Release notes describing deltas and limitations honestly;
   PyPI is optional and a separate publication action.

### Example

```sh
python3 -m pip install git+https://github.com/holland202/vacuity_lint.py.git@v1.1.0
vacuity-lint --version
vacuity-lint . --format json
```

**Do not run the tag-based command until GitHub confirms that v1.1.0 exists.**
For pre-release testing use the exact source commit SHA instead.

### Risk and compatibility

The precision changes can alter some heuristic classifications and counts;
the API's documented stability covers **rule IDs and exit code meaning**, not
the set of files flagged by future versions. Unlike a stable parser's exact
source line, a file-level finding lacks trustworthy `line` data; the JSON
intentionally omits this field.

**Stop after release:** the next engineering change should be a separate issue
supported by user-reported examples, not an automatic expansion of v1.1.0.

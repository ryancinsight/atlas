<a id="atlas-tool-pin-manifest"></a>
## ATLAS-TOOL-PIN-MANIFEST — Gate tool versions are written at their install sites, not in one manifest [verification] [patch] — todo
- outcome: one committed manifest pins nextest, semver-checks, deny, audit, llvm-cov and mutants; each atlas install step reads its version there, and a test fails a step that differs.
- evidence (basis b334401f2fcf): `nextest@0.9.140` and `cargo-semver-checks@0.51.0` are literals in three workflows; `cargo-deny` is unpinned; audit, llvm-cov and mutants appear in no workflow or script.
- oracle: `python -m pytest scripts/tests/test_tool_manifest.py -q` (not written; exits 4 today) passes with every workflow `tool:` pin equal to the manifest and all six tools listed.
- basis: b334401f2fcf; priority: verification; needs: none; scope: workflows, `pre-push`, manifest; next step: extend `scripts/semver-tool.toml` or add a sibling, decided with ATLAS-CHANGELOG-GENERATOR.

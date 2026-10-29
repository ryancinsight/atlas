<a id="atlas-coeus-cpu-overlay"></a>
## ATLAS-COEUS-CPU-OVERLAY — Repair generated overlay exports [patch] — todo
- Outcome: generated patches omit deleted coeus-leto paths and root Cargo gates resolve exported revisions outside the development overlay.
- Oracle: pinned generation is byte-exact and idempotent, reports no missing providers or freshness errors, contains no coeus-leto, and the normal candidate gate passes.
- priority: correctness
- needs: none
- scope: .cargo/config.toml; member hook gitlinks; scripts/git-hooks/pre-push; scripts/atlas_build_inputs.py; scripts/atlas_cast_gate.py; scripts/atlas-lock-form.py; affected tests; ADR 0064.
- Next step: deliver the generated configuration and matching export gate against the oracle.
- Verification: configured focused Python tiers, real-Cargo export cases, native-owner boundary cases, normal root gate, and independent source/object review.
- basis: 4f7824e1045380f81d9349923d1c48b12bef40bd
- Links: [PR #551](https://github.com/ryancinsight/atlas/pull/551), [ADR 0064](../docs/adr/0064-shared-build-source-identity.md).

<a id="atlas-coeus-cpu-consumer-migration"></a>
## ATLAS-COEUS-CPU-CONSUMER-MIGRATION — Migrate out-of-repo coeus-leto consumers to coeus-cpu [major] — todo
- Outcome: `leoneuro-segmentation` (leoneuro-rs), `ritk-model`, and `ritk-tensor-ops` (ritk) build against `coeus-cpu`, with no `coeus-leto` reference in their manifests, sources, or docs.
- Evidence: coeus PR #608 (merge 58ee4963) renamed `coeus-leto` to `coeus-cpu` per coeus ADR 0080; the three consumers still pin the `coeus-leto` name at Coeus 0.10.0 (ritk workspace manifest, ritk-model/ritk-tensor-ops manifests, ritk `docs/architecture.md` + `docs/book/leto_integration.md`; leoneuro-rs workspace manifest + leoneuro-segmentation manifest + `model.rs` `coeus_leto::RandomScalar` bounds). Their lockfiles pin pre-rename revs, so they build today and break at their next Coeus pin advance.
- Oracle: each consumer's own gate suite green with its Coeus pin at or past 58ee4963; `git grep -n 'coeus[-_]leto'` in each repo returns nothing outside its changelog.
- Landed 2026-10-19: ritk half delivered in lane `build/ritk-coeus-cpu-migration` (45bcd5dac) — full satellite advance to coeus 0.12, `coeus-cpu` in the workspace, no `coeus[-_]leto` left in manifests, sources or docs; workspace gates green offline (5572 passed). Unpushed; needs its PR to land before leoneuro can pin the migrated ritk. Remaining: leoneuro-rs only.
- priority: architecture
- needs: none
- scope: repos/leoneuro-rs (default branch is the live peer branch `codex/private-atlas-migration` — coordinate, do not cut across it), repos/ritk (main checkout holds unrelated WIP — work in a lane).
- Next step: land the ritk lane's PR, then migrate leoneuro-rs on its live peer branch (advance the whole Coeus family to 0.12 together; rename the dep + `use` paths, port 0.10→0.12 breakage, regenerate the lock).

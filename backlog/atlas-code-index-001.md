<a id="atlas-code-index-001"></a>
## ATLAS-CODE-INDEX-001 — Search-ladder infrastructure for context economy [patch] — in-progress

- Owner: opencode-2026-08-05; scope: the atlas meta-repo and its `repos/*` members
  (tooling and generator contract only — no member Cargo.toml/manifest edits).
  Host tooling verified: `rust-analyzer` and nightly toolchain present; `ast-grep`
  absent (install is scope item 1).

- Policy: AGENTS.md context_and_memory "Code-search ladder". Motivation: 325 tool-output truncations and 66 compactions across eight recent fleet sessions — agents read where they should search; the fleet-recommended tools were researched and the ladder chosen over them where they misfit (agent-memory graph stores such as Graphiti duplicate the board/ADR/git memory layer and are rejected — one curated memory, one archive).
- Scope: (1) ast-grep availability as committed tooling (structural queries, stateless per tree — worktree-safe by construction); (2) SCIP emission per member repo (`rust-analyzer scip`), revision-keyed under a gitignored index directory with a generator-contract freshness check, plus a thin lookup wrapper (scip CLI) so agents resolve definitions/references without full-file reads; (3) rustdoc JSON as the machine-readable API oracle for the anti-hallucination check, emitted under the nightly verification toolchain like miri; (4) evaluate a Zoekt trigram server over the shared gitdirs only if per-tree tooling proves insufficient at fleet scale — standing infrastructure needs the toil-automation justification; (5) wire ladder usage guidance into each repo agent-facing docs if repo convention keeps local instructions.
- Acceptance: spot-check — an agent locates three symbol definitions and one API signature across repos it has not read this session using only ladder queries (no full-file reads); index freshness check green in the sweep.


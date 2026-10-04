<a id="atlas-hook-rustdoc-doc-false"></a>
## ATLAS-HOOK-RUSTDOC-DOC-FALSE - Skip the rustdoc identity step for undocumented libs [patch] - todo
- outcome: the member pre-push gate runs its rustdoc identity step (`scripts/git-hooks/pre-push:1260`) only for packages whose lib target is documented; a `[lib] doc = false` package (consus-python) produces no rustdoc artifact, so the step fails every push that touches it.
- acceptance: the gate reads each changed package's lib-target `doc` flag from `cargo metadata` and skips the rustdoc identity step when it is false; a hook test pushes a change to a `doc = false` fixture package and passes, and a documented package with a rustdoc warning still fails.
- priority: verification
- needs: none
- scope: `scripts/git-hooks/pre-push`, `scripts/tests/test_atlas_pre_push_gate.py`.
- next: find where the gate builds `identity_cargo_manifest_args` for rustdoc and add the metadata filter there.
- evidence: consus#122 push refused on `consus-python` with fmt, clippy, and nextest green.
- basis: 0fd74ea6e28b (atlas origin/main when filed).

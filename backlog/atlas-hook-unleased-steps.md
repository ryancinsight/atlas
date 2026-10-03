<a id="atlas-hook-unleased-steps"></a>
## ATLAS-HOOK-UNLEASED-STEPS - A clone without the stack checker gates its steps with no lease [verification] - todo
- priority: verification
- basis: 3ea1f0629
- outcome: a pre-push gate of a clone with no reachable stack checker takes the same source-identity leases as one with it, or refuses to run its cargo steps unleased and says why; the claim in the hook and ADR 0064 that each step takes the leases of the packages it builds holds for every gate.
- evidence (2026-10-02): when `identity_checker` is not a file, the steps of `scripts/git-hooks/pre-push` run `cargo clippy`, `cargo nextest` and `cargo doc` directly, with no lease and no record (the same on main). Two such gates of one repository, or one beside a stack gate, write the same target directory with nothing excluding them.
- acceptance: (1) a test runs the hook in a clone with no stack checker and shows each cargo step either holding the leases of its packages or not started; (2) the ref lock's comment and ADR 0064's pre-push section stop qualifying the claim.
- needs: none
- scope: `scripts/git-hooks/pre-push`, `scripts/atlas_build_identity.py`, `scripts/tests/test_atlas_pre_push_gate.py`
- next: decide between taking the leases from the checker vendored beside the hook and refusing, from how many clones lack it (`git grep -n identity_enabled`).

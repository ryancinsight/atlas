<a id="atlas-v1-milestone-ladders-001"></a>
## ATLAS-V1-MILESTONE-LADDERS-001 — Roll the 1.0 milestone ladder out to every member [arch] — todo
- priority: correctness; owner: atlas coordinator (member lanes execute in their own repos).
- outcome: every member ships a release-scope ADR, a `backlog/milestones.md` ladder, and `milestone:` assignments on its backlog items, in provider-first order; the atlas V1 path (member ladders + publish chain + parity M4) reads as one ordered plan instead of three.
- context: six members landed ladders on 2026-11-09 under the harmonia template (release-scope ADR + `backlog/milestones.md` + per-item `milestone:` assignments, each milestone closing only on exit checks at a fetched default-branch commit):
  - harmonia `7040bb539` (ADR 0005), horae `569763eb2`, hyperion `f0a15a20`, iris `9da14ae6`, melinoe `e75f94d`, proteus `fe2ee9a`.
  - measured 2026-11-10 at atlas `6483806bc`: 6 of 28 members have ladders; 22 remain.
  - eunomia lane delivered 2026-11-10: ADR 0012 + `backlog/milestones.md` on
    branch `docs/eunomia-milestone-ladder-20261110` at `cd84a3d` (PR #193, open);
    ladder count becomes 7 of 28 on merge.
- template (do not reinvent per member): release-scope ADR named `<n>-release-scope-1-0.md` (Accepted, scope in/out with veto points, rejected alternatives, overturning evidence); `backlog/milestones.md` with `M-*` milestones each carrying `exit:` commands, `needs:` edges, and non-goals; every open correctness/verification item assigned to exactly one milestone; the 1.0 milestone blocks on release authority and never forces `publish = true` without it.
- remaining order (provider-first, so consumer ladders can cite provider exits):
  1. foundation/compute: eunomia, aequitas, themis, mnemosyne, moirai, hermes, leto, hephaestus;
  2. providers: apollo, athena, proteus (done), harmonia (done), horae (done), hyperion (done), iris (done), melinoe (done), asclepius, tyche, consus, gaia, prometheus, ares;
  3. integrators: CFDrs, helios, kwavers, ritk, metis.
- acceptance per ladder: (a) release-scope ADR accepted in the member; (b) every open correctness/verification item carries a `milestone:` assignment; (c) each `M-1.0` exit names `cargo semver-checks`, publish dry-run readiness, `cargo doc`, and zero open correctness items; (d) atlas records the member's ladder commit SHA here as delivered.
- needs: none (member-local docs work; no cross-repo code). Blocked-by: nothing at atlas level.
- non-goals: changing any member's API or exit thresholds from atlas (member ADR owns that); advancing gitlinks (rides the normal pointer-advance chore); the publish chain itself (ATLAS-PUB-002/003/005/006/008/010/011/012/013/015) and parity M4 exits (`docs/parity/execution.md`), which this item sequences after the ladders, not inside them.
- next: claim the foundation wave (eunomia first — every ladder above it cites scalar law); file one member-lane task per repo in the order above, each `needs:`-edged on its providers' delivered ladders.

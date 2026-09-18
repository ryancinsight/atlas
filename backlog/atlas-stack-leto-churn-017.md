<a id="atlas-stack-leto-churn-017"></a>
## ATLAS-STACK-LETO-CHURN-017 — Upstream working-tree churn blocks consumer verification — todo

Third occurrence on 2026-07-31 of the same pattern, now costing real delivery
time, so it is recorded as its own item rather than re-diagnosed each session.

- **Symptom**: a consumer repo's `cargo check`/`nextest` fails inside
  `repos/leto` with errors that change between consecutive runs and reference
  code the consumer never touched.
- **Cause**: the stack `[patch]` overlay resolves first-party dependencies to
  local working trees, so a peer's *uncommitted, mid-edit* state in an upstream
  repo reaches every downstream consumer immediately. Observed today in
  `leto-ops/src/application/attention/` (cleared on retry) and
  `leto-ops/src/application/zip.rs` (still red; file modified seconds before
  each check).
- **Not a defect in either repo.** The overlay behaving as designed, plus
  normal peer activity. Same class as ATLAS-RITK-MODULE-FORWARD-000.
- **Cost**: any consumer increment depending on the churning crate cannot be
  verified, so it cannot be committed. ATLAS-COEUS-NLLS-004 parked on exactly
  this for roughly 25 minutes, clearing only when the peer committed `zip.rs`.
  The park was the correct call — the errors changed between consecutive runs,
  so retrying would have chased a moving target — but it is dead time that
  option (b) would remove.
- **Candidate directions, needing a decision rather than more diagnosis**:
  (a) accept it and treat upstream redness as a park-and-switch signal, which is
  current practice and what the contention response order already prescribes;
  (b) have the overlay resolve to each member's last *committed* revision rather
  than its working tree, making peer WIP invisible until committed — this is the
  real fix but changes the development overlay contract in
  architecture_scoping and needs an ADR;
  (c) narrow the overlay per session to the repos an agent actually edits.
  Option (b) is the recommendation: an uncommitted edit is not a published
  state, and the overlay currently makes it one for the whole stack.
- **Class**: `[arch]` if (b) is taken, since it revises the development overlay.
- **Fourth occurrence 2026-08-13 falsifies option (c).** Verifying one RITK
  branch, four consecutive attempts minutes apart each failed in a *different*
  upstream repo: `eunomia` (duplicate `PartialEq` — macro added before the
  manual impls were removed), `apollo-fft` (`BLUESTEIN_NATIVE_PHASE_TRIG` used
  in impls before the trait declared it), `eunomia` again (`FloatElement`
  gaining an `Accumulator` associated type, trait ahead of impls), and
  `consus-hdf5` (arity mismatch mid-signature-change). Every one is a normal
  half-finished edit; none is a defect.
  Option (c) assumed churn localizes to the repos an agent is near, so a
  narrowed overlay would dodge it. It does not: the churn was spread across
  four repos the RITK branch never touched, and narrowing enough to avoid them
  would exclude most of the stack, which defeats the overlay. That leaves (a)
  and (b), and (b) remains the recommendation.
  Retrying is also not free-but-harmless: because the failing crate *moves*,
  a green run is a peer-quiet window rather than evidence, so a consumer needs
  a retry loop that distinguishes upstream churn from its own redness before
  any result means anything.


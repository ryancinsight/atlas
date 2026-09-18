<a id="atlas-hermes-consumer-entry-2026-08-25"></a>
## ATLAS-HERMES-CONSUMER-ENTRY-2026-08-25 — Restore Hermes as the stack's lane-kernel owner [arch] — in-progress

- **Outcome:** a consumer anywhere in the stack writes one generic lane kernel
  against `hermes-simd` and gets per-ISA machine code for it, so the provider
  table's assignment of "CPU lane-parallel kernels and ISA dispatch" to `hermes`
  holds in fact and not only on paper.
- **Finding:** four members carry lane-parallel ISA kernels outside Hermes —
  `apollo` (28 files, 90 `#[target_feature]`), `kwavers` (AVX-512 FDTD
  stencils), `CFDrs` (`cfd-core/src/compute/simd/`), and `moirai`
  (`moirai-utils/src/simd/arch/`). The common cause is upstream and is not a
  preference: Hermes exports no route into a `#[target_feature]` scope, so a
  consumer's generic kernel compiles at baseline features — the outcome Hermes
  ADR 009 exists to prevent. Full scan and per-file classification in
  `gap_audit.md`, finding 2026-08-25.
- **Sequence** (upstream first; a consumer migrated before the capability exists
  would have to invent a second abstraction over the first):
  1. `HS-FEARLESS-TOKEN-2026-08-25` in `hermes` — value-carrying capability
     token, a `vectorize`-class entry, and a safe operation surface over the
     existing facets. Filed, hermes PR #62 merged the audit that drives it.
  2. `ATLAS-APOLLO-ISA-FORK-2026-08-25` in `apollo` — largest consumer, filed
     and blocked on step 1.
  3. `kwavers` and `CFDrs` — file per-repo items once step 1 lands and step 2
     has established the migration shape. Not filed yet on purpose: their
     migration pattern should follow a worked example, not precede it.
  4. `moirai` — blocked on a topology question, not on step 1. The README
     places `moirai` below `hermes`, so it cannot take that edge without
     inverting the documented order, and neither crate depends on the other
     today. Settle the direction first; an ADR revision may be the deliverable
     rather than a migration.
- **Open ownership question:** `eunomia`'s packed-unpack intrinsics
  (`packed/unpack/intrinsics/{avx2,avx512,neon}.rs`) sit in Eunomia while the
  provider table gives packed-lane representation to Hermes, which re-exports
  them. Resolve when step 1 lands; Eunomia's F16C conversion path is its own
  bounded context and is not in question.
- **Acceptance oracle:** the `core::arch` and `#[target_feature]` census in the
  finding above is re-run and every consumer row is zero or a recorded
  sanctioned remainder, with each migrated family carrying differential tests
  against its scalar path and no benchmark regression against a recorded
  baseline. The census is the tracked metric and ratchets downward.
- **Risk / change class:** [arch] at stack level; each member's own increment is
  classified in that member.
- **Required authority:** Change on allowlisted repositories; no release.
- **Status 2026-08-25:** **step 1 delivered** — hermes PR #63 merged as
  `85655c05`, gitlink advanced. `hermes_simd::vectorize` plus `LaneKernel<T>`
  give a consumer one route into a `#[target_feature]` scope, and nine safe
  operations (`mul_add` and the cross-lane permutes) complete `Vector`'s
  surface for multiply-accumulate kernels. Codegen measured: 41 ymm-bearing
  instructions including `vfmadd213ps` with no call into the backend
  operations through the entry, against zero ymm and five outlined calls
  without it. ADR 016.

  Two things narrowed against the filed plan, both recorded in the hermes audit
  amendment: the safe surface already existed on `Vector` so only FMA and the
  permutes were missing, and ADR 011 needed no revision because it already puts
  the safe layer above unsafe facets. One unforeseen blocker was cleared on the
  way: `#[runtime_dispatch]` dropped doc comments, which is why no dispatcher in
  that crate could be `pub`.

  **Step 2 ran, and changed the campaign.** `apollo-fwht` was migrated onto the
  entry, measured, and reverted: 1.6x to 8.8x slower than the code it would
  replace across three dispatch placements (apollo PR #112, measurements in
  `repos/apollo/gap_audit.md#fwht-vectorize-negative`). Two structural
  mechanisms, now recorded upstream in hermes ADR 016 and its README:

  - The `#[target_feature]` scope does not follow a closure onto another thread,
    so wrapping a work-partitioning call applies the ADR 009 penalty by way of
    the mechanism meant to remove it.
  - Hermes' `Scalar` backend is a plain array loop the optimizer inlines and
    auto-vectorizes at the build's baseline ISA. For a bandwidth-bound
    elementwise kernel it beats an explicit backend path, because there is no
    arithmetic for wider registers to save and the dispatch boundary is pure
    overhead.

  **This item is therefore rescoped from a census to a measurement gate.** The
  `core::arch` counts identify candidates; they do not establish that migrating
  one is an improvement. Each family needs a before/after measurement, and a
  family that measures slower stays as it is with the measurement recorded.

  On that criterion `kwavers`' AVX-512 FDTD stencils are the most promising
  remaining candidate — compute-dense, large per-call work units — and `CFDrs`'
  elementwise `cfd-core` kernels the least. Steps 3 and 4 stay unfiled: filing
  them as migrations would presume the conclusion this measurement removed.
  Step 4 (`moirai`) remains gated on the layering question, not on the
  capability.

  The acceptance oracle above is revised accordingly: the census ratchets toward
  zero only for families a measurement supports converting, and a recorded
  sanctioned remainder now includes "measured slower under the entry".


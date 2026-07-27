# ADR 0034: Athena carries one accelerator backend over Hephaestus, not a per-device crate

- Status: Proposed
- Date: 2026-07-27
- Class: [major] [arch]
- Relates to: [ADR 0022](0022-horae-athena-provider-extraction.md),
  [ADR 0033](0033-krylov-ownership-reaffirmation.md)

## Context

ADR 0022 states that Athena does **not** own "accelerator devices, buffers,
transfers, sparse kernels, reductions, or dispatch, which remain in
Hephaestus". Athena's justification for existing as a separate provider is
exactly that its recurrences span both a host substrate (Leto) and an
accelerator substrate (Hephaestus) — a solver that only ever ran on host
arrays would belong in Leto.

The current crate topology does not match that justification:

```text
crates/athena-wgpu/src/backend/kernels/
├── axpy.rs        # hand-written WGSL compute shader
├── direction.rs   # hand-written WGSL compute shader
├── residual.rs    # hand-written WGSL compute shader
├── scale.rs       # hand-written WGSL compute shader
└── update.rs      # hand-written WGSL compute shader
```

Two defects follow.

**Athena authors GPU kernels.** `axpy`, `scale`, `residual`, the CG direction
recurrence, and the fused CG update are vector kernels and dispatch — the
categories ADR 0022 assigns to Hephaestus. Hephaestus already exposes `dot`
and `norm_l2` over device buffers and carries an `elementwise` module, so this
is duplicated capability, not a gap Athena had to fill.

**The GPU dimension is forked to one device API.** Hephaestus supports four
device backends — `hephaestus-cuda`, `hephaestus-metal`, `hephaestus-rocm`,
`hephaestus-wgpu`. Athena supports one, and adding CUDA under the present
shape would mean an `athena-cuda` crate with its own CUDA kernels, then
`athena-metal`, and so on. That is the consumer-owned per-vendor backend
anti-pattern: a consumer owning its own vendor backends re-forks the exact
dimension the substrate exists to own. The crate name also puts a device API
in Athena's public surface, where vendor names belong only to device-impl
crates inside the substrate.

This is the same class of defect as the Leto Krylov regression in ADR 0033,
mirrored onto the accelerator side: capability that belongs to a substrate
provider was rebuilt in the consumer.

## Decision

1. Athena carries exactly **two** backend crates: one over Leto for host
   execution, one over Hephaestus for accelerator execution. Neither names a
   device API.
2. Replace `athena-wgpu` with `athena-hephaestus`, implementing
   `KrylovBackend` against the device-API-neutral Hephaestus surface so Athena
   inherits CUDA, Metal, ROCm, and WGPU without a crate per device. Device
   selection stays Hephaestus's runtime-detection concern, not a Cargo feature
   or a crate choice in Athena.
3. Delete Athena's WGSL kernels. Every vector operation the `KrylovBackend`
   contract requires — `copy`, `scale`, `axpy`, `dot`, `norm_l2`, `residual`,
   `fused_cg_update`, `combine_direction` — resolves to a Hephaestus kernel.
4. Where Hephaestus lacks a required primitive, implement it **upstream in
   Hephaestus** as a generic device kernel, never downstream in Athena. The
   two fused Krylov-shaped operations (`fused_cg_update`, `combine_direction`)
   are the likely additions; both are ordinary vector kernels with no solver
   knowledge, so they sit correctly in the substrate.
5. No compatibility re-export of `athena-wgpu`. The crate is removed, and its
   consumers — presently only Athena's own tests — move in the same change.

## Consequences

- Athena's accelerator support widens from one device API to four in a single
  change, and future Hephaestus device backends are inherited at no cost.
- `athena-wgpu` disappears from the published crate set. It is not yet
  depended on by any repository outside Athena, so the break is confined.
- `KrylovBackend` is unchanged. `athena-core` recurrences, including the CG,
  GMRES, and BiCGSTAB families, are untouched by this ADR.
- Hephaestus gains two vector kernels it does not currently expose. They are
  generic over its scalar and dialect traits, so every device backend gets
  them from one implementation.
- The `fused_cg_update` and `combine_direction` methods on `KrylovBackend`
  encode a solver-shaped fusion in a storage contract. They are retained for
  now because they exist to let a device fuse two traversals into one
  dispatch, which is a genuine backend concern; whether they survive is
  revisited once the Hephaestus kernels land.

## Verification

- Board item `ATLAS-ATHENA-ACCEL-BACKEND-001`.
- Residue scan: no `wgsl`, `@compute`, or `workgroup` literal anywhere in
  `repos/athena`; no crate under `repos/athena/crates` names a device API.
- The existing GMRES and CG WGPU contract tests pass unchanged against the
  Hephaestus-backed backend, plus the BiCGSTAB contract added under ADR 0033
  stage A.
- Hephaestus additions carry their own differential tests against the CPU
  reference path, per the existing accelerator-kernel convention.

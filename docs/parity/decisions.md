# Scope and architecture decisions

Program 2026-10-26.1 / [contracts](contracts.md).

The user authorizes full functional parity, while Atlas retains first-party
providers, native arithmetic, generic static dispatch and acyclic ownership.
These constraints govern implementation; they do not remove comparator APIs.
This decision register records conflicts that need architecture review before
affected implementation starts. No entry grants sign-off for an architectural
or public breaking change. Existing required ADR reviews remain mandatory.

| ID | Conflict and consequence | Accountable owner / required decision |
| --- | --- | --- |
| DEC-001 | Atlas README says “displaces, not API compatibility”; historical Leto ndarray/nalgebra and Coeus PyTorch/JAX/MLX sets omit requested NumPy/TF capabilities. | Atlas: accept the four-framework functional-equivalence denominator; preserve historical bounded claims with dated scope corrections. Rust API spelling may differ; observable functional semantics may not disappear. |
| DEC-002 | Coeus ADR0025 retires external performance comparisons; the requested parity program requires independently comparable correctness and performance evidence. | Coeus + Atlas: amend via normal ADR review to run pinned external oracles outside production, with native tests still mandatory. Reopen TF and performance obligations. |
| DEC-003 | NumPy object/structured/string/datetime/masked arrays and TF string/resource/variant/ragged values exceed numeric `Scalar` scope. | Coeus owns tensor semantics; Leto owns host arrays; Eunomia owns numeric representations; Consus owns encoding. Specify nonnumeric element/record contracts without forcing them into numeric arithmetic or dropping them. |
| DEC-004 | JAX/PyTorch/TF tracing, compilation, graph transformations, export, custom derivatives and effect/resource handling exceed current eager/autodiff surfaces. | Coeus owns functional graph/AD/compiler semantics; Hephaestus owns target lowering/device mechanics; Moirai owns scheduling. Design a first-party IR/transform boundary, not XLA/libtorch/TF runtime embedding. |
| DEC-005 | TPU/custom accelerator, CUDA/ROCm/Metal/WGPU paths and distributed collectives need real hardware; current bounded backends and “available adapter” early returns do not prove these. | Hephaestus owns target mechanics; Themis placement, Melinoe capability proofs, Moirai execution. Record target feasibility, hardware acquisition and capability reports. Unavailable targets block corresponding parity. No CPU substitution. |
| DEC-006 | Legacy graph/session/control-dependency, estimator/compat namespaces, extension/custom-op interfaces, Keras, mobile/serving/browser and framework-specific tools may not appear in core API extraction. | Atlas and Coeus: enumerate every public documented namespace and linked companion surface; classify versioned/deprecated/experimental entries separately, retaining obligations until an explicit scope decision. Do not treat “legacy” as excluded. |
| DEC-007 | Identical operation names have conflicting dtype promotion, aliasing, mutation, randomness, complex gradients and reduction determinism. | Owner of each canonical operation: retain framework-specific semantic variants and negative-domain tests. One generic implementation may use explicit type-level policies; aliases and compatibility facades do not prove equivalence. |
| DEC-008 | Existing publication workflows may continue when the historical baseline cannot compile; that is insufficient for this new 1.0 program. | Atlas/release owners: require an exact-revision SemVer verdict plus fresh published dependency resolution. Reconcile Atlas #540 through its owner; do not weaken current checks or mutate that branch. |
| DEC-009 | New graph/IR, dtype and backend boundaries can trigger [arch]/[major] ADR sign-off. | Respective provider owner: produce concrete contracts/design and obtain required sign-off before architectural implementation. User authorization to proceed does not fabricate existing required review. |

Decision state is **open** for all entries. Program definition cannot be called
complete until their semantic and ownership consequences are reviewed and
materialized. The requested capabilities remain in the denominator meanwhile.
For architecture-neutral tooling WP-002, none of these decisions blocks the
local implementation or review.

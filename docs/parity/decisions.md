# Scope and architecture policy decisions

Program 2026-10-26.3. [Machine register](decisions.json).

The existing user direction resolves the initial nine policy choices: full parity is the
denominator, and native first-party generic provider design governs implementation.
No scope reduction or additional user approval is needed to select these policies.
This resolves the earlier open-policy register; it does not grant provider ADR
sign-off or claim that the corresponding semantic/design work is complete.

## DEC-001 — atlas

The reference denominator includes all public documented capabilities of all four frozen releases; functional API spelling may differ. Historical displacement/seeded implementation sets do not limit scope.

Rejected alternatives: Limit parity to existing provider APIs; Require third-party runtime API identity.

Impact: Reject the implemented-subset denominator. Keep every candidate until reviewed public/alias/capability disposition; all retained public capabilities need complete variants.

Remaining work: No unresolved scope choice. Operation contracts and extraction closure remain work.

## DEC-002 — coeus

Pinned external correctness and performance oracles run in isolated test/benchmark environments; production computation remains first-party native Rust.

Rejected alternatives: Retire all external performance comparisons; Embed comparator runtimes in production.

Impact: Add TensorFlow and the complete comparator union without deleting native tests or legacy MLX coverage. Prior Burn/performance retirement does not waive this program.

Remaining work: Amend the affected repository ADR through normal required review before implementation gates change.

## DEC-003 — leto

Include nonnumeric, structured, string, temporal, masked, ragged, resource and variant values wherever public references support them. Numeric Scalar remains an arithmetic contract; representation/element/resource contracts stay with existing owners.

Rejected alternatives: Exclude nonnumeric types; Coerce every value into numeric Scalar.

Impact: Leto owns host values/layout; Eunomia numeric representation; Coeus tensor/program/resources; Consus encodings. User-defined extension behavior remains a protocol obligation.

Remaining work: Concrete element/resource interfaces and public changes need provider ADR/design review; no new API sign-off is asserted.

## DEC-004 — coeus

Include tracing, compilation, graph/control effects, transforms, custom rules and export under first-party Coeus program semantics, Hephaestus target lowering and Moirai execution.

Rejected alternatives: Call external XLA/libtorch/TF as the implementation; Stop at eager tensor and reverse AD APIs.

Impact: Plan an acyclic first-party IR/transform/target boundary and retain all framework-specific effects/shape/cache/export contracts.

Remaining work: Concrete IR, compiler and extension designs require normal architecture approval.

## DEC-005 — hephaestus

Every reference-valid target remains required; use actual native execution and explicit capability/unsupported-target errors. Missing hardware blocks execution qualification, not the definition or the denominator.

Rejected alternatives: Count CPU fallback as device parity; Exclude unowned or unavailable accelerators.

Impact: Separate per-target capabilities and native evidence, including TPU/custom devices. Define procurement/access as implementation prerequisites without changing credentials or permissions.

Remaining work: Target designs and actual hardware qualification remain pending; no app/service deployment authorization implied.

## DEC-006 — atlas

Retain documented legacy/versioned/experimental public APIs, language/extension interfaces and reachable companion tools in the frozen scope, with explicit stability and separate source provenance.

Rejected alternatives: Discard deprecated/experimental symbols; Treat root package declarations as all tooling.

Impact: Resolve generated/inherited/re-exported identities and workflow capabilities. A private spelling or repeated declaration is not alone an exclusion/alias proof.

Remaining work: No scope reduction is approved. Any future irreconcilable architecture limitation must retain the obligation and identify the decision needed.

## DEC-007 — eunomia

One canonical algorithm may expose explicit semantic/precision policies; distinct framework promotion, aliasing, mutation, RNG and AD rules stay distinct variants. Equivalence requires a source/domain proof, not equal names.

Rejected alternatives: Collapse equal symbol names; Clone algorithms per dtype/backend; Hide intermediate widening in generic T code.

Impact: Reference-required accumulation/rounding must be expressed by explicit associated accumulator/arithmetic policy with numerical derivation. Native-T invariants stay enforced; differing result profiles cannot be silently dropped.

Remaining work: Precision/element policies and numerical analyses need provider review. No implicit widen-compute-narrow path is authorized.

## DEC-008 — atlas

1.0 requires an exact-revision SemVer verdict, successful package graph resolution, registry/artifact receipts and clean fresh consumers before downstream release.

Rejected alternatives: Treat an unbuildable baseline as a passing verdict; Publish first and verify consumers later.

Impact: Historical workflow skip/continuation paths cannot certify the new program. Preserve #540 and other owner branches; integrate through the responsible owner.

Remaining work: Actual baseline/release graph repairs and normal required CI/reviews remain pending.

## DEC-009 — atlas

Public/architectural changes receive their existing required ADR/design/code reviews on the exact candidate before implementation/integration qualification.

Rejected alternatives: Treat user goal as fabricated ADR sign-off; Request the user to reapprove already authorized routine planning.

Impact: The user authorizes definition and implementation work, not false review evidence or hold bypass. Architecture-neutral tooling proceeds with ordinary independent review.

Remaining work: Each affected provider owns concrete reviews; there is no remaining generic scope ambiguity requiring a user question.

The source and semantic denominator still requires closure. Missing hardware,
provider implementation, reviews, and performance evidence are release/implementation
blockers; they do not justify silently excluding a documented capability. A
specific architecture choice can be marked design-approved only with its actual
required review evidence. No such sign-off is created by this register.

## DEC-010 — leto

Preserve NumPy special-method lookup behavior by execution phase. Exact builtin
bypasses, absent attributes, any lookup exception consumed as absence, successful
noncallable lookup and actual invocation are distinct typed outcomes. Later
metadata/coercion/invocation errors follow their source-defined branches. Opaque
outputs preserve identity and existing AD behavior. Diagnostics add no callbacks,
exceptions or ownership/lifetime changes.

Rejected alternatives: return a new caller error for consumed lookup failure;
clear later errors under a broad fallback; retain/format exception objects in a
way that changes observable behavior. Full parity and typed phase/context
retention jointly select this policy. Concrete provider design/ADR review and
all implementation/execution evidence remain pending.

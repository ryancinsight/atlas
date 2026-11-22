# ADR 0072: Qualify the stable stack from independently versioned member contracts

- Status: Proposed
- Date: 2026-11-22
- Class: [arch]
- Owners: Atlas for the integrated revision, member maintainers for their public contracts.

## Context

Atlas pins 28 independent repositories. RITK scopes its stable milestone to a viewer, Apollo versions its transform crates independently, and Kwavers already distributes several major versions. Coeus ADR 0083 records a delivered tensor milestone. The Atlas reference program still has open API mappings and no recorded execution evidence. Harmonia and Hyperion use Git distribution. Two otherwise publishable crates require Harmonia.

## Decision proposed for review

Use the member's release-scope ADR to identify its stable public surface and distribution channels. Record each in-scope package, its candidate revision, version, compatibility baseline and intended artifact. A crate already at a stable major keeps its major according to SemVer. Private tools and application binaries use their declared channel. Document the support decision for a public pre-1.0 sibling, such as Kwavers Driver, before closing its repo's plan.

A member milestone closes on the exact candidate when its named exits and standing checks pass. For the integrated stack, every member must additionally satisfy its row in the [repository register](../parity/repositories.json), including assigned parity capabilities or real consumer qualification. Atlas also requires complete reference definition, the per-API evidence and the release verdict at a coherent set of gitlinks. Record both verdicts with their own evidence.

Sequence a selected cohort by the required **crate** dependencies in ADR 0060. A compatible, verified 0.x upstream can satisfy a member's current contract, as Aequitas ADR 0020 permits. Check each enabled optional feature against the actual resolved graph. For a private required provider, either obtain its owner's distribution decision and verify the resulting artifact, or keep the downstream registry release blocked. A Git-only consumer uses a pinned source and clean build. Where the existing Atlas evidence schema requires registry evidence for a Git-only member, the Atlas owner must secure review of a channel-specific gate or obtain the required receipt. Keep the gate open in the interim.

## Alternatives and consequences

A synchronized version bump would misstate compatibility for independent crates and regress shipping major versions. Using local milestone exits as a stack-wide verdict would omit large reference and device obligations. Requiring every provider to publish 1.0 before any consumer can develop would invalidate existing, supported registry cohorts. The proposed approach allows independent development while preserving the final coherent graph and every remaining evidence obligation.

## Verification and reconsideration

Recompute the crate order on the exact gitlinks, compare candidate API surfaces with released baselines and replay each claimed consumer outside the checkout. In the [qualification program](../parity/README.md), both definition and release must pass with reviewed evidence on the final revisions. Reject closure if a private required edge survives packaging, an artifact identifies a different source revision, or a skipped native job is the only evidence for a supported target. A change to a member's distribution policy or a capability's owner requires a new review at that boundary.

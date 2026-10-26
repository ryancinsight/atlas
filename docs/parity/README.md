# Four-framework functional parity program

Program revision: **2026-10-26.2**. Protocol: **1**. State: **definition in progress; no 1.0 qualification**.

This is the canonical Atlas program for the October 26 instruction to complete
Coeus and its providers to full NumPy, JAX, PyTorch and TensorFlow functional
parity under Atlas design principles. It does not change any package version.
The [backlog entry](../../backlog/atlas-full-parity-001.md) owns coordination;
repository backlogs continue to own implementation. Earlier displacement and
bounded-scope completion claims do not establish this program's completion.

| Artifact | Authority |
| --- | --- |
| [Program manifest](program.json) | Version, frozen reference snapshots, completeness and required gates |
| [Reference inventories](reference/) | Extracted public API identities, source versions, hashes and extraction gaps |
| [Capability contracts](capabilities.json) | Single accountable owner, provider prerequisites, semantics, tests and qualification obligations |
| [Contracts and evidence protocol](contracts.md) | Coverage axes, evidence states, equivalence and rejection rules |
| [Work packages](work-packages.json) and [execution program](execution.md) | Dependency order, readiness, estimates, acceptance and handoffs |
| [Repository criteria](repositories.json) | Each registered repository's 1.0 entry and exit obligations |
| [Provider audit](provider-audit.md) and [source evidence](provider-evidence.json) | Revision-specific reconciliation of existing claims |
| [Decisions](decisions.md) | Architectural conflicts that cannot silently reduce scope |
| [Validation](validation.md) | Reproduction commands, executed checks, limitations and independent review |

The inventory denominator is the union of each frozen framework's public
documented surface, with framework/version/symbol/kind retained. Matching names
are not evidence of matching semantics. A capability family is a routing and
acceptance contract, **not** an assertion that its API rows are mapped or
implemented. Extraction completeness, per-API semantic mapping and execution
coverage have separate denominators. Unknowns remain visible and block the
corresponding milestone. A finite starter inventory never establishes a
complete denominator.

Run `python3 scripts/atlas-parity.py check` to validate the inventory and program,
`python3 scripts/atlas-parity.py report` for counts, and
`python3 scripts/atlas-parity.py qualify --gate definition` to evaluate the
definition exit. A structurally valid program may still fail qualification.
Release qualification additionally requires exact-revision evidence and all
repository and cross-repository gates. Skips, absent hardware, silent CPU
fallback and exclusions are never successful qualification.

The selected first implementation slice is the Atlas traceability/evidence
validator (WP-002). It enforces this distinction with rejection tests. Provider
repairs remain with their existing owners; no protected branch is modified.

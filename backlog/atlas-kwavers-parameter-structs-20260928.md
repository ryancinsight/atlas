<a id="atlas-kwavers-parameter-structs-20260928"></a>
## ATLAS-KWAVERS-PARAMETER-STRUCTS-20260928 — Collapse 260 `clippy::too_many_arguments` suppressions into parameter structs [minor] — todo
- priority: tightening
- outcome: kwavers' 316 `allow_sites` are 82% one lint — 260 `too_many_arguments` suppressions (audit §6, docs/audit/2026-09-26); each call family takes a parameter struct so the suppression deletes, never re-relaxes. Oracle: `atlas-conformance.py report --repo kwavers` reads `allow_sites` ≤ 56 with no other class raised, touched crates' suites green per increment.
- next: enumerate sites per crate; one module family per increment (struct + every call site in the same change), no new `#[expect]`.

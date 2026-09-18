<a id="atlas-privacy-naming-1"></a>
## ATLAS-PRIVACY-NAMING-1 — Private consumer named throughout stack artifacts [chore] — todo (needs user decision)

outcome: decide whether `repos/leoneuro-rs/`'s owning org name counts as confidential for artifact purposes, then apply (or record as not applying) the standing rule that a private consumer's name never appears in stack artifacts — only a gitignore entry, with upstream items citing it generically.

Decision needed: the name currently appears in ~12 references across `backlog.md`, `gap_audit.md`, `docs/adr/0036-neuroimaging-and-mr-ownership.md`, and `PATH_DEP_AUDIT_001_ENTRY.md`, including a closed audit ledger and an Accepted ADR. If confidential: one deliberate forward-only sweep rewrites references generically, preserving each record's meaning (git history keeps the old text). If not: record that the standing rule does not apply here.

Adjacent, unrelated: `PATH_DEP_AUDIT_001_ENTRY.md` sits at repo root (no loose report files permitted); its content belongs in the closed item it serves.

Owner: unclaimed.

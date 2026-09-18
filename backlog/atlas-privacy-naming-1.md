<a id="atlas-privacy-naming-1"></a>
## ATLAS-PRIVACY-NAMING-1 — Private consumer named throughout stack artifacts [chore] — todo (needs user decision)

- Owner: unclaimed; scope: `backlog.md`, `gap_audit.md`,
  `docs/adr/0036-neuroimaging-and-mr-ownership.md`, and
  `PATH_DEP_AUDIT_001_ENTRY.md`.
- The consumer at `repos/leoneuro-rs/` is a private external org's code drop:
  gitignored at `.gitignore:60`, no `.gitmodules` entry, no
  `submodule.*` keys, remote on a different GitHub org. ATLAS-GIT-HYGIENE-001
  confirmed that arrangement is deliberate design, not a stale rule.
- Standing policy for such a consumer is that it stays out of the stack map
  entirely — the gitignore entry is the only sanctioned trace, and upstream
  items it motivates cite "a downstream consumer" generically. Its name is
  currently in four tracked artifacts, including an ADR and the closed
  audit ledger, across roughly a dozen references.
- I redacted only the one reference I added myself (in
  ATLAS-OVERLAY-GEN-STALE-1's measurement). The rest is **not** being swept
  unilaterally: several sit in closed items' audit trails and an Accepted ADR,
  where a blind rename would break the traceability those records exist to
  provide, and peers reference those item names.
- The decision needed: does this consumer's name count as confidential for
  artifact purposes? If yes, the sweep should be one deliberate pass that
  rewrites references generically and preserves each record's meaning
  (git history keeps the old text either way — the redaction is forward-only).
  If no, the standing rule should be recorded as not applying here, so this
  keeps being re-raised.
- Adjacent, unrelated to the naming question: `PATH_DEP_AUDIT_001_ENTRY.md` sits
  at the repository root, where the root-manifest rule admits no loose report
  files. Its content belongs in the closed item it serves.


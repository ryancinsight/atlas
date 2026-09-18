<a id="atlas-kwavers-default-recheck-2026-08-18"></a>
## ATLAS-KWAVERS-DEFAULT-RECHECK-2026-08-18 — moving default remains open — todo

- Kwavers PR #400's orphan-module cleanup is merged at
  `23f53284d789ba9b15788b51b3e83e40d301caf3`; its formatting prerequisite PR
  #403 is merged at `15c12732f5841125a5d65b6c3da2adc0f7c0793a`. The clean
  `kwavers-orphan-096` lane had no uncommitted state and was removed; its
  branch ref remains recoverable.
- The provider default now includes the Atlas wheel-parity closure at
  `e6fb53b90798f498e87d2c1fed275944a5cbe4b6`. Hosted run `32237250724`
  passes the complete wheel matrix and installed-wheel k-Wave comparator at
  its preceding source head `56bded6fa`; the Atlas pointer advances to the
  documented current default for exact-head coherence.
- PR #402 is not the current default proof: it is open at
  `d8886b032c50c7ebbcc2f12ebaceacabe95e19f1` with `mergeStateStatus=CONFLICTING`.
  Its earlier `69478221f` evidence is stale. Re-open the consumer integration
  and pointer advance only after the peer-owned branch is reconciled or the
  provider default independently satisfies the hosted matrix.


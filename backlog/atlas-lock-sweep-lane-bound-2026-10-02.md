<a id="atlas-lock-sweep-lane-bound-2026-10-02"></a>
## ATLAS-LOCK-SWEEP-LANE-BOUND-2026-10-02 — Every member lock advances to the named provider merges [correctness] — blocked
- priority: correctness
- outcome: `scripts/atlas-lock-sweep.py` advances every member's `Cargo.lock` to named provider merges with no member skipped, and `python scripts/atlas-stack-overlay.py check` reports no `PIN DRIFT` outside members another sweep owns.
- done so far: the tool needs no lane (#463), resumes a sweep whose branch exists (#466), and returns sources a moving head carried past its target (#471). Lock PRs merged for apollo, athena, mnemosyne, moirai, hermes, ares, proteus, horae, themis, harmonia and gaia, whose gitlinks advance in the delivering PR; at those gitlinks none of the eleven drifts.
- blocker: eunomia 0.9.0 (ryancinsight/eunomia#154) and leto 0.44.0 (ryancinsight/leto#318) landed mid-sweep. aequitas, hyperion, leto and prometheus require `eunomia ^0.8`, so their locks cannot resolve until [ATLAS-PROVIDER-VERSIONS-20261002](atlas-provider-versions-20261002.md) lands. metis waits on ryancinsight/metis#468 ([ATLAS-MNEMOSYNE-08-SWEEP](atlas-mnemosyne-08-sweep.md)).
- re-open trigger: ATLAS-PROVIDER-VERSIONS-20261002 merged for those four members, and metis#468 merged.
- next: `python scripts/atlas-lock-sweep.py --heads --open-prs --members aequitas,hyperion,leto,metis,prometheus`, then one batched gitlink advance.
- basis: a92f185288e3a768b3efa2a4992578eb7ac74e9f

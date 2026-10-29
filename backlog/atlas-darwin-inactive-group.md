<a id="atlas-darwin-inactive-group"></a>
## ATLAS-DARWIN-INACTIVE-GROUP — Prove Darwin process-group inactivity before accepting cleanup EPERM [patch] — todo

- priority: correctness
- outcome: cleanup accepts an already inactive Darwin process group without hiding permission failures for executable or unknown members.
- evidence: a fresh direct child with its own session exits normally and remains unreaped; its PID equals its process-group ID and its state is `Z`. On the published baseline, cleanup reports `Operation not permitted` although reaping returns zero.
- mechanism: the shared runner inspects the system libproc state after Darwin `killpg` returns EPERM. It accepts only a complete, unchanged membership list whose members all have matching PID/group and zombie state. Incomplete, changing, unreadable and live states retain the failure.
- runtime contract: the isolated scanner loads adjacent runtime modules, and the trusted rescue export carries the complete module set. Archive production must finish successfully before extraction and execution.
- fixture contract: removing owned fixture symlinks never changes the permissions of their external targets or follows dangling links.
- acceptance: native zombie-only cleanup succeeds; live and unknown groups fail; native ABI/error cases fail closed; copied scanner/rescue/root-hook/checkout runtimes remain complete and resist hostile sibling imports; readonly-tree tests preserve external targets; unchanged complete Python tiers and applicable delivery gates pass.
- scope: `scripts/darwin_process.py`, shared process cleanup, isolated scanner/rescue runtime exports, their regression tests, and ADR 0067. No member pins, hook fingerprints, dependency baselines, manifests or lockfiles change.
- next: independent final-revision review and normal local/hosted qualification before default-branch delivery.
- needs: none
- basis: 6e495c8246be86bfd4c30613326f77294fd26dc9

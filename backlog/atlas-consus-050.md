<a id="atlas-consus-050"></a>
## ATLAS-CONSUS-050 — Coordinate Consus 0.5 storage adoption [major] — in progress
- outcome: Consus owns shared MAT v5 decoding, and the seven Atlas consumers resolve the same Consus 0.5.0 revision.
- evidence: all 17 crates are verified at released Consus `2193675`. All seven storage consumer PRs and eight subsequent downstream repository updates landed. Registry and fresh-consumer checks verify the 20 Apollo releases, eight Coeus 0.13.0 packages, and 15 authorized RITK versions. See the [integration audit](../gap_audit.md#consus-050-adoption).
- priority: correctness; needs: Atlas release checks and a coherent Aequitas stack; scope: Consus storage consumers; next: align the remaining allocator locks and Aequitas 0.5 provider defaults, then verify the integrated Atlas revision. The remaining 11 authorized RITK versions await three registry prerequisites.

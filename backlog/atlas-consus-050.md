<a id="atlas-consus-050"></a>
## ATLAS-CONSUS-050 — Coordinate Consus 0.5 storage adoption [major] — in progress
- outcome: Consus owns shared MAT v5 decoding, and the seven Atlas consumers resolve the same Consus 0.5.0 revision.
- evidence: all 17 crates are verified at released Consus `2193675`. All seven consumer PRs landed. Gaia Mesh 0.7.0 and the six Hephaestus 0.29.0 releases pass fresh registry consumer tests. The gitlinks and [integration audit](../gap_audit.md#consus-050-adoption) record the tested revisions.
- priority: correctness; needs: Atlas release checks and a coherent Aequitas stack; scope: Consus storage consumers; next: finish the Apollo and Coeus registry sequence, verify the eligible RITK archives, and reconcile the final consumer locks with the provider defaults before landing Atlas.

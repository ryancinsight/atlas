<a id="atlas-secret-scan-allowlist-source"></a>
## ATLAS-SECRET-SCAN-ALLOWLIST-SOURCE - Read the secret allowlist from a trusted revision [patch] - todo
- outcome: `scripts/atlas-secret-scan.py` reads `.secret-scan-allowlist` from the revision being scanned (`allowlist(root, rev)`, line 131), so a pushed commit can allowlist the secret it introduces; the allowlist is read from the fetched default branch, the same trusted source the hooks already resolve the scanner from.
- acceptance: a push whose commit adds a credential and its fingerprint to `.secret-scan-allowlist` is blocked; an allowlist entry already on the default branch still suppresses its finding; tests cover both.
- priority: correctness
- needs: none
- scope: `scripts/atlas-secret-scan.py`, `scripts/git-hooks/pre-push`, `.githooks/pre-push`, the scanner's tests.
- next: pass the trusted revision into `allowlist()` from each caller; decide how an allowlist change itself lands (reviewed PR to the default branch).
- evidence: independent review of atlas#369.
- basis: 0fd74ea6e28b (atlas origin/main when filed).

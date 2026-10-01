<a id="atlas-identity-lease-starvation"></a>
## ATLAS-IDENTITY-LEASE-STARVATION - Gated pushes starve on the 900 s identity-lease wait [verification] - todo
- priority: verification
- basis: 1b92f219b
- outcome: a gated member push under fleet load waits at most one peer gate step for a source-identity lease. It is never refused for a lease another push holds through a whole gate.
- evidence (2026-09-30): eight serial pushes were refused after the 900 s wait (helios, ritk, hephaestus, kwavers, metis, CFDrs, and #408 four times), and on 2026-10-01 the hephaestus and both ritk pushes again. In the hephaestus refusal, a ritk gate held `hephaestus-rocm` at ritk's revision.
- measured scope: one `atlas-build-identity.py run` covers one step of one package (`scripts/git-hooks/pre-push`, the per-package clippy, tests and rustdoc loops). The step takes a shared lease on every first-party path dependency in the package's closure (`scripts/atlas_build_artifacts.py` `dependency_snapshot`, `clean_packages`). It takes exclusive only on the packages it must clean, then downgrades and runs cargo (`scripts/atlas_build_identity.py`, the `with ExitStack()` block). No lease spans steps.
- hypothesis (unverified): two gates that resolve one package from different sources (ritk through the overlay's main tree, the hephaestus gate from its own export) each find the other's artifacts foreign. Each takes the package exclusive, cleans and rebuilds it, so every hold includes a rebuild. Verify by logging cleaned packages per step across one concurrent ritk + hephaestus pair; if the cargo unit hash already differs per source path, key the lease by package and source.
- acceptance: (1) a test with two runs on one closure records the second run's wait as bounded by the first run's hold of that step; (2) the pre-push hook refuses a second concurrent push of the same ref and repository; (3) a timed fleet push records per-step lease hold.
- needs: none
- scope: `scripts/atlas_build_identity.py`, `scripts/atlas_build_artifacts.py`, `scripts/atlas_build_lease.py`, `scripts/git-hooks/pre-push`, `scripts/tests/`
- next: run the hypothesis check above. A repository-name filter on `clean_packages` is rejected: it would skip verifying the very dependency artifacts the shared lease protects.

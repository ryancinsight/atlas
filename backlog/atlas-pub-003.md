<a id="atlas-pub-003"></a>
## ATLAS-PUB-003 — Register trusted publishers and remove the unused PyPI token [chore] — todo
- owner: user-gated (registry/GitHub settings are Ask-User; agent prepares, verifies, never registers). [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §4.
- outcome: every package has a trusted publisher registered (owner `ryancinsight`, caller's workflow filename) — no long-lived credential remains in the stack. State: crates.io has `eunomia`/`aequitas` published; PyPI has 8/10 bindings live (missing `helios-python`, `ritk`). crates.io needs one manual first publish before trusted publishing bootstraps.
- next per crate: resolve name (ATLAS-PUB-006) -> first publish (crates.io only) -> register trusted publisher -> enable enforcement. Acceptance: one trusted-publishing release per package; `pypi` API token deleted.
- residual: unregistered package fails closed at auth (intended); a pending PyPI publisher does not reserve the name until first use.

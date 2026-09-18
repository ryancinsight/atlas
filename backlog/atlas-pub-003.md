<a id="atlas-pub-003"></a>
## ATLAS-PUB-003 — Register trusted publishers and remove the unused PyPI token [chore] — todo

- Owner: user-gated — registry and GitHub settings changes are Ask-User actions;
  an agent prepares the values and verifies the result, it does not perform the
  registration.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §4.
- Outcome: every publishing package has a trusted publisher registered on the
  target registry, so no long-lived registry credential exists anywhere in the
  stack. Values per package: owner `ryancinsight`; repository = the package
  repository; workflow filename = the **caller's** filename
  (`rust-release.yml` / `python-release.yml`), because the OIDC claim carries the
  caller's identity, not the Atlas reusable workflow's; environment `crates-io` /
  `pypi`.
- Registry verification 2026-07-28: crates.io **cannot bootstrap** a new crate
  through trusted publishing — the crate must already exist and the first publish
  requires an API token. PyPI **can** bootstrap through a pending publisher
  configured under the account sidebar.
- **Registry state re-verified 2026-09-04; the 2026-07-28 line "no Atlas crate is
  published" is stale.** On crates.io: `eunomia` 0.8.0 and `aequitas` 0.2.0 are
  published from this account, both dated 2026-08-02. On PyPI, **eight of the ten
  binding distributions are live**: `cfd-python` 0.1.6, `apollo-fft` 0.2.0,
  `coeus-python` 0.9.0, `consus-python` 0.1.0, `hephaestus-python` 0.18.0,
  `kwavers-python` 0.1.0, `leto-python` 0.41.0, `moirai-python` 0.4.0. Not
  published: `helios-python` and `ritk`. So the bootstrap question is settled for
  most of the stack and the open work is metadata quality, not first publication
  — see `#python-blank-pypi-pages`.
- Sequence per crate, therefore: (1) resolve its registry name (ATLAS-PUB-006 for
  the twelve collisions); (2) one manual publish from the local Cargo credential
  store, in workspace dependency order; (3) register the trusted publisher;
  (4) enable trusted-publishing-only enforcement. PyPI distributions skip step 2.
- Acceptance: one trusted-publishing release succeeds per package; the API token
  in the `pypi` environment is deleted afterwards; trusted-publishing-only
  enforcement is enabled in each registry's settings once its pipeline is proven.
- Residual risk: an unregistered package fails closed at the auth step. That is
  the intended failure mode, not a regression. A pending PyPI publisher does not
  reserve the project name until first use, so a name can be lost in between.


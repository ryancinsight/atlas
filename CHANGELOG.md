# Changelog

## Unreleased

### Changed

- Merge Apollo PR #46 at `11fd1d0`; partition GPU dispatch verification into
  a deep private leaf and retain Hephaestus/Leto provider ownership.
- Advance the Atlas Apollo gitlink in PR #18 at `56ad179`.
- Keep Kwavers PR #292 at `5f9e97b` pending its required hosted matrix; no
  dirty parent gitlink is advanced.
- Advance the RITK gitlink to its verified Apollo 0.24 source-checkout repair
  on `main`.
- Refresh Apollo, Hephaestus, Kwavers, Leto, and RITK gitlinks to the current
  provider graph; add ADR 0020 with the exact provider-graph closure theorem.
- Align public Atlas submodule pins with their fetched default branches.
- Advance Apollo, Helios, and RITK gitlinks to their merged default-branch
  commits after their provider and cross-platform CI closure.
- Advance the Apollo submodule pin after its concurrent provider-boundary merge.
- Advance the CFDrs and Hephaestus gitlinks after their typed GPU boundary
  closure.
- Advance the CFDrs gitlink after executable one- and two-dimensional
  validation examples replaced static reports on `main`.
- Advance the RITK gitlink after its merged lock metadata repair aligned the
  Hephaestus patch entries with the current provider graph.
- Register Kwavers and Helios in the Atlas public submodule roster.
- Reject bare `cargo test` in cross-stack drivers while retaining doctests.

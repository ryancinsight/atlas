# Changelog

## Unreleased

### Changed

- Advance the fixed Kwavers integration pin to `2fb8661`, which synchronizes
  Apollo `0.24.0` in the consumer lockfile.
- Refresh the fixed Kwavers Atlas provider graph to current Apollo,
  Hephaestus, Kwavers, Leto, and compiling RITK commits; document the exact
  gitlink closure theorem in ADR 0020.
- Align public Atlas submodule pins with their fetched default branches.
- Advance the Apollo submodule pin after its concurrent provider-boundary merge.
- Register Kwavers and Helios in the Atlas public submodule roster.
- Reject bare `cargo test` in cross-stack drivers while retaining doctests.

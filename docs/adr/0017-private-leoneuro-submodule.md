# ADR 0017: Private LeoNeuro submodule in public Atlas

- Status: accepted
- Change class: [arch]
- Date: 2026-07-13

## Decision

The public `ryancinsight/atlas` meta-repository tracks the private
`LeoNeuro-INC/leoneuro-rs` repository at `repos/leoneuro-rs`. This deliberately
exposes the organization/repository name, submodule URL, tracked branch, pinned
commit, and Atlas relationship. Source contents remain private and require
LeoNeuro-INC authorization.

The LeoNeuro workspace consumes the adjacent migrated Kwavers checkout at
`repos/kwavers`; it does not vendor Kwavers or recreate its APIs through an
adapter.

## Verification

- GitHub reports `LeoNeuro-INC/leoneuro-rs` as private.
- The gitlink resolves to the reviewed LeoNeuro source commit.
- Cargo metadata resolves every direct Kwavers package from
  `D:/atlas/repos/kwavers` and the shared target from `D:/atlas/target`.
- An unauthenticated recursive clone may fail at the private submodule by design;
  authenticated LeoNeuro-INC clones must succeed after the source branch passes
  its full Rust gate and becomes `main`.

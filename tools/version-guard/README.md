# Atlas version guard

The `scan` command checks declared version movement in one member's diff.
The `coherence` command compares version requirements with package manifests
from the repositories registered in Atlas's `.gitmodules`.

## Coherence identity

The package index uses **(registered provider, package name)**. A provider's
Git URL is compared without a trailing `.git` and without ASCII case
differences, as in first-party URL detection. Registrations of that same URL
share an identity. A registration without a URL uses its member path instead.
Versions are values of this key: conflicting versions of the same package
within one provider fail the scan. Different packages within a provider may
have different versions, and independent repositories may each own an `xtask`.

A dependency's `path` or `git` source selects the provider before its package
name (including `package =` aliases) is looked up. A package absent from that
source never falls back to a same-named package in another provider. As before,
registry-only declarations and declarations without a version constraint are
outside this requirement comparison. This scan is not a Cargo resolver and
does not diagnose every missing package or unsupported manifest construct.

Inherited workspace dependencies retain their declaration manifest, so their
relative paths use the declaring workspace's directory. Workspace dependency
and version inheritance select the nearest scanned workspace root; an empty
inner workspace never falls through to an outer workspace's declaration.
Any `workspace.*` table also establishes its implicit parent workspace table.
Explicit `package.workspace` overrides are not resolved by this parser.

Working-tree dependency paths use filesystem canonicalization. Remote-tree
paths use lexical containment because a newly added crate may have no local
directory yet. The most specific registered root owns a path; conflicting
identities at that depth produce an error. The existing `.gitmodules` parser's
path deduplication remains unchanged.

## Validation

From a directory outside the Atlas checkout, with the committed Rust version,
run `cargo test --manifest-path /path/to/atlas/tools/version-guard/Cargo.toml
--locked`, then Clippy for all targets and Rustfmt. This standalone tool check
avoids applying the stack's development overlay to the tool's own lockfile.
It does not replace the normal Git hooks or the root coherence sweep, which
still measures the registered provider graph and reports requirement drift.

`tests/coherence_identity.rs` exercises the public scan with independent helper
versions, source-specific path/Git aliases, inherited and nested workspaces,
registry collisions, same-provider version conflicts, and local Git trees
containing an unmaterialized remote target. Resolver unit tests cover ambiguous
path ownership and lexical escapes. The original coherence tests remain intact
in `src/coherence/tests.rs`.

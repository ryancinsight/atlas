# Atlas provider checkout

`atlas-provider-checkout` reads one Cargo manifest, finds external sibling
paths in dependency, patch, and replacement sections, resolves each provider
through an exact Atlas commit, and materializes the recorded gitlink revision.
Existing provider directories are reused only when they are real, clean
checkout directories already at the required revision; symlinked provider
paths are rejected so an alternate checkout cannot impersonate the canonical
destination.

Consumers call the composite action at an exact Atlas SHA:

```yaml
- uses: ryancinsight/atlas/.github/actions/checkout-path-dependencies@<atlas-sha>
  with:
    manifest: consumer/Cargo.toml
    destination: .
    atlas_ref: <atlas-sha>
```

`manifest` and `destination` are relative to `GITHUB_WORKSPACE`. Internal paths
below the manifest repository remain untouched. The destination is canonicalized
before materialization; every external path must fall below
`destination/<provider>`, and every resulting dependency directory must contain
`Cargo.toml`. Moving `main`, stale hard-coded provider lists, wrong-revision
reuse, dirty reuse, symlinked provider paths, missing provider URLs, and paths
outside the authorized destination fail closed.

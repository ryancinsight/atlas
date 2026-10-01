<a id="atlas-pub-012"></a>
## ATLAS-PUB-012 - Release tags take the ecosystem form `<package>-v<version>` [verification] - todo
- priority: verification
- outcome: crate releases are tagged `<package>-v<version>` (the cargo-release/release-plz form) instead of `crate-<package>-v<version>`, whose `crate-` prefix is a type marker on a tag.
- evidence (2026-10-01): `crates-publish.yml` defaults `tag-prefix` to `crate-` on main. ritk (`crate-ritk-image-v0.4.0`) and apollo (`crate-apollo-fft-v0.26.0`) carry such tags, beside unprefixed ones (`kwavers-optics-v3.0.0`, `apollo-wavelet-v0.10.0`). The version-change publishing in #408 keeps the same default so both paths agree.
- acceptance: the `tag-prefix` default is empty in both shared workflows and the crates-pending action; the release-event path still resolves the package from either tag form, with a test per form; no existing tag is rewritten.
- needs: none (start once #408 has merged, since it adds the third default)
- scope: `.github/workflows/crates-publish.yml`, `.github/workflows/crates-publish-pending.yml`, `.github/actions/crates-pending/`, `scripts/tests/`
- next: read how `crates-publish.yml` maps a release tag to a package, and whether any member caller passes `tag-prefix` explicitly.

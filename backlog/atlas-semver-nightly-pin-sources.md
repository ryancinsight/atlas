<a id="atlas-semver-nightly-pin-sources"></a>
## ATLAS-SEMVER-NIGHTLY-PIN-SOURCES — The SemVer rustdoc nightly pin has no owner file [patch] — todo
- outcome: the SemVer gate's rustdoc nightly is named in one committed file that the workflows, the test and ADR 0069 read or cite, so moving the pin is one edit.
- evidence (origin/main b334401f2fcf; judge finding F8): `nightly-2026-08-01` is written at `python-tests.yml:161`, `semver-gate.yml:122` and `test_atlas_semver_pr.py:128`; ADR 0069 cites the absent owner file.
- oracle: `git cat-file -e HEAD:scripts/semver-rustdoc-toolchain.txt` exits 0; `git grep -n -E 'nightly-[0-9]{4}-[0-9]{2}-[0-9]{2}' -- .github scripts docs/adr` lists the owner alone; a test asserts each consumer equals it.
- basis: b334401f2fcf; priority: verification; needs: none; scope: the owner file, its consumers, ADR 0069; next step: land the file (held on `refs/pull/784/head`, unread there), then convert the consumers.

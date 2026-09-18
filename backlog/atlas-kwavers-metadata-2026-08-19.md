<a id="atlas-kwavers-metadata-2026-08-19"></a>
## ATLAS-KWAVERS-METADATA-2026-08-19 — Python surface consistency — blocked

- Kwavers commit `e62d529e6` removes the unused workspace `pyo3` ABI3
  declaration, keeps the binding and release floor consistently at Python 3.8,
  repairs the Python documentation URL, and makes Pages rebuild on source and
  manifest changes. Atlas tracks it at root commit `a2f46dc`.
- `cargo fmt --all -- --check`, `git diff --check`, and locked metadata
  inspection pass. The provider `cargo check -p kwavers-python --locked` is
  blocked before compilation by the shared Atlas overlay requesting lockfile
  updates for unused local patches; no source failure is inferred.


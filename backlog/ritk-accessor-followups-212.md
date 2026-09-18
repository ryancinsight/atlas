<a id="ritk-accessor-followups-212"></a>
## RITK-ACCESSOR-FOLLOWUPS-212 — Two consequences the accessor migration exposed [patch] — blocked

**Sharpened: the `Result` is now provably uninhabited, and the sibling makes
it explicit.** On `refactor/ritk-two-accessors-047`, `extract_vec`'s body is
`image.data_cow_on(&B::default()).into_owned()` — infallible — while its
signature is still `anyhow::Result<(Vec<f32>, [usize; D])>`. There is no
longer any fallible operation inside the wrapper at all.

Beside it sits `extract_vec_infallible`, which does the **identical** thing
without the wrapper, and whose own Rustdoc states the truth: "canonical Coeus
host extraction is infallible". So the codebase already contains the
correction — added as an additive `_infallible`-suffixed sibling rather than
applied to the original, which is the marker-naming and compatibility-soup
pattern in one.

The fix is one function, not two: `extract_vec` becomes infallible,
`extract_vec_infallible` is deleted, callers drop their `?`.

**Scoped as its own atomic `[patch]`, to land immediately after `-047`
merges.** The two names carry **518 call sites** (183 + 335). Folding that
into `-047` would triple a branch already held for review and is precisely
the "branch grows past its item" pattern — the same call made for apollo's
827-site `precise`/`reduced` rename. Sequenced after the merge because `-047`
is what removes the last fallible operation; before it, the `Result` is
merely near-dead rather than provably dead.

- Second half unchanged: ~14 `.into_owned()` sites can drop the copy, since
  `Cow` derefs. Same commit is fine — both are mechanical over the same
  surface.
- Acceptance: zero `_infallible`-suffixed siblings; `extract_vec` returns a
  tuple; no call site carries `?` on it; workspace green.

- `ritk_tensor_ops::extract_vec` now has a **visibly fake `Result`**. It is
  pre-existing, but was hidden one level down inside `try_data_vec`; removing
  that wrapper surfaced it. A `Result` whose error branch is unreachable is
  the same defect the `try_` pair carried.
- ~14 `.into_owned()` sites can drop the copy entirely, since `Cow` derefs.
  Kept out of `-047` deliberately: that migration was held
  semantics-preserving, and turning it into a performance change mid-flight
  would have made the semver evidence harder to read.


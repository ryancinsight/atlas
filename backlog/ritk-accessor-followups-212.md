<a id="ritk-accessor-followups-212"></a>
## RITK-ACCESSOR-FOLLOWUPS-212 — Two consequences the accessor migration exposed [patch] — blocked

- outcome: `extract_vec` becomes infallible (its body is already
  `image.data_cow_on(&B::default()).into_owned()`, no fallible op remains);
  `extract_vec_infallible`, an additive sibling doing the identical thing,
  is deleted; callers of both (518 sites: 183 + 335) drop their `?`. ~14
  `.into_owned()` sites also drop the copy, since `Cow` derefs.
- blocked on / re-open trigger: `refactor/ritk-two-accessors-047` merging —
  `-047` removes the last fallible operation; before it, the `Result` is
  near-dead rather than provably dead. Scoped as its own atomic `[patch]`
  deliberately: 518 call sites would triple an already-held review branch.
- acceptance: zero `_infallible`-suffixed siblings; `extract_vec` returns a
  tuple; no call site carries `?` on it; workspace green.

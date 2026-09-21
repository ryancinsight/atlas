<a id="ritk-views-047"></a>
## RITK-VIEWS-047 — Collapse seven data accessors to two [major] — blocked
outcome: seven RITK data accessors collapse to two survivors — `data_slice() -> Result<&[T]>` and `data_cow_on(&B) -> Cow<[T]>` — with zero re-export/deprecated/forwarding shims, and `CartesianGridGeometry` promoted to public + generic over rank.
- State: landed on `refactor/ritk-two-accessors-047` (`cfba6507`), **not merged** — a breaking public-API removal ([major]) holds for an independent verdict rather than self-review.
- Gates green: fmt 0, clippy `--workspace --all-targets -D warnings` 0, nextest 5332 passed/25 skipped (298s), doctests 0, `semver-checks --baseline-rev bacfe1f6` 195 pass/1 fail (the expected `inherent_method_missing` naming exactly the five removed methods).
- Evidence caveats: crates.io semver run is vacuous (0/253 skipped, blocked by an unrelated ritk-image version bump) — the `--baseline-rev` run is the real evidence; confirmatory nextest re-run stalled at 4730/5332 under peer build contention with zero failures, so the reported green figure predates the final rustfmt/doc edits.
- **Blocked on:** independent judge confirming (1) the five removals are the complete break set, (2) the 28 deleted `?` sites on the removed `try_` pair were genuinely unreachable, (3) the two extracted transform cores are equivalent. Then merge and advance the gitlink.

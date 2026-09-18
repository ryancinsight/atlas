<a id="kwavers-elastic-constructors"></a>
## ATLAS-KWAVERS-ELASTIC-CONSTRUCTORS-2026-09-06 - kwavers#707 is red on real errors and conflicting [patch] - todo

Parent: [`#proteus-elastic-ssot`](backlog.md#proteus-elastic-ssot).

- **outcome:** the construction half of the Proteus elastic delegation lands,
  completing the item whose accessor half landed as
  [kwavers#724](https://github.com/ryancinsight/kwavers/pull/724).
- **state:** [kwavers#707](https://github.com/ryancinsight/kwavers/pull/707),
  open since 2026-09-04, `CONFLICTING`, every CI job red. It covers
  `constructors.rs`, `elastic.rs`, the heterogeneous factory, and the
  homogeneous implementation — disjoint from #724's `computed.rs` and
  `mod.rs`, so the two are complementary halves rather than duplicates.
- **the red is not the pin.** It was worth checking, since the dead mnemosyne
  rev broke every kwavers build until #723; but the log shows real compile
  errors: `E0277` (`T: eunomia::traits::field::RealField` unsatisfied) and
  several `E0034` (multiple applicable items in scope). The second is the
  characteristic hazard of exactly this delegation — provider trait methods
  colliding with the type's inherent methods of the same name — so the
  diagnosis points at the design, not at the environment.
- **method:** rebase onto current `main` (which now carries both the repoint
  and #724), then resolve `E0034` by choosing at each site whether the inherent
  or the provider method is the intended one rather than disambiguating
  mechanically. The bound failure is likely a missing `RealField` on a generic
  parameter the delegation newly requires.
- **taken over 2026-09-06** as
  [kwavers#727](https://github.com/ryancinsight/kwavers/pull/727); #707 closed
  with the diagnosis recorded on it.
- **the red was against a stale base, not a defect in the change.** Rebased
  onto current `main` — which now carries the mnemosyne repoint (#723) and the
  accessor half (#724) — the `E0277` and `E0034` errors are gone. Worth
  recording as a pattern: a long-open PR's red is a claim about a base that no
  longer exists, and re-measuring it costs one rebase.
- **merged 2026-09-08.** #727 was a draft because `cargo clippy --all-targets`
  could not run at all: its dev-dependencies reach `ritk`, whose resolution
  failed on the Moirai requirement lag. That same lag was what the SemVer gate
  failed on — that job runs `cargo update` per crate, and every crate failed
  identically. Once kwavers' sweep leg landed on `main`, merging the base in
  (not rebasing, so the PR history stayed reviewable) picked up the `0.6.0`
  requirement and unblocked both. Full gate then: check, `clippy --all-targets
  -- -D warnings`, 215 tests, fmt — all clean, including the check that had
  never been able to run.
- **the two halves of `#proteus-elastic-ssot` are now both on kwavers `main`**,
  so `lame_from_speeds` and the duplicated Lamé conversion algebra are gone
  from the consumer.
- **the seven mnemosyne phase commits were not carried over:** they chase
  revisions on a closed pull request's branch and `main` pins the merged
  result, the same finding as gaia's series.


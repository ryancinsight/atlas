<a id="ritk-views-047"></a>
## RITK-VIEWS-047 — Collapse seven data accessors to two [major] — blocked

Landed on `refactor/ritk-two-accessors-047` (`cfba6507`), **not merged**: a
breaking public-API removal is `[major]`, so it holds for an independent
verdict rather than self-review.

The deferral that kept this open was arithmetic, not difficulty. ADR 0019's
"681 call sites across ~250 files" counted every call to any of the seven
accessors — including the 565 on `data_slice`, one of the two that *survive*.
The accessors that had to go carried **60 sites**; all 60 migrated, with no
re-export, `#[deprecated]`, or forwarding wrapper. ADR 0019 now carries a
dated revision note correcting the figure; ADR 0021 records the decision.

Survivors chosen on caller evidence: `data_slice() -> Result<&[T]>` (565 sites
want a contiguous borrow and already handle the strided failure) and
`data_cow_on(&B) -> Cow<[T]>` (59 want the layout-independent form; the 50
wanting ownership get it from either). The removed five were a
default-backend axis crossed with an ownership axis. The `try_` pair was
worse than redundant — its own Rustdoc said extraction "succeeds for every
valid image", so **28 sites carried a `?` on a branch that cannot be taken**.

Transform consolidation rode along: `CartesianGridGeometry` promoted from
`pub(crate)` in ritk-filter to public in ritk-spatial and generic over rank,
with a typed `NonCartesianGrid` error replacing a message that named its
first caller. Four sites became consumers rather than an eighteenth
implementation; both `apply`/`apply_native` core pairs were verified
byte-identical by `diff` before extraction (`inverse_displacement` 738→583,
`iterative_inverse_displacement` 393→263). Net **−529/+655 across 47 tracked
files plus 3 new** — a reduction while adding a public module and 3 tests.

**Gates** (`+1.97.0-x86_64-pc-windows-msvc`, exit codes from files not pipes):
fmt 0 · clippy `--workspace --all-targets -D warnings` 0 · nextest
**5332 passed / 25 skipped**, 298s, 0 slow · doctests 0 · `semver-checks
--baseline-rev bacfe1f6` **195 pass / 1 fail**, the failure being
`inherent_method_missing` naming exactly the five removed methods and nothing
else.

Two evidence caveats recorded rather than smoothed: the crates.io
semver run is **vacuous** (0 checks / 253 skipped) because ritk-image's
0.3.0→0.4.0 bump predates this work and makes the major lints unrunnable —
the `--baseline-rev` run is the real evidence; and the confirmatory nextest
re-run stalled at 4730/5332 under peer build contention with **zero
failures**, so the green figure above is from the run before the final
rustfmt-whitespace and documentation edits.

**Acceptance for merge:** an agent that did not author it confirms the five
removals are the complete break set, the 28 deleted `?` sites were genuinely
unreachable, and the two extracted cores are equivalent. Then merge and
advance the gitlink.


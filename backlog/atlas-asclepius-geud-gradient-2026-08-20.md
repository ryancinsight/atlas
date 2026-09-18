<a id="atlas-asclepius-geud-gradient-2026-08-20"></a>
## ATLAS-ASCLEPIUS-GEUD-GRADIENT-2026-08-20 — Add an independent Coeus gradient oracle [patch] — in-progress

The Asclepius Coeus adapter test currently compares its reverse-mode gradient
with a second hand-coded power-mean derivative. That is a useful algebraic
check but not an independent behavioral oracle: the same formula can be wrong
in both places. The provider backlog already identifies a central-difference
check for this seam as `ASC-VER-018`.

**Scope:** Asclepius `crates/asclepius-coeus/tests/equivalent_uniform_dose.rs`
on a clean lane based on fetched `origin/main`, plus root PM entries. Add a
finite-difference value oracle for the existing dose fixture and derive its
step/tolerance from floating-point scale and central-difference truncation.
Do not alter the adapter implementation, peer-owned book/PM files, or the
Atlas Iris lane.

**Acceptance:** the test evaluates the adapter at independently perturbed dose
vectors, compares central differences with the reverse-mode gradient under a
documented bound, covers every dose coordinate, and fails under a mutation of
the adapter's gradient path; focused/full provider gates pass and the exact
branch is published for review.

**Owner:** current Atlas session. **Claimed files:** Asclepius
`crates/asclepius-coeus/tests/equivalent_uniform_dose.rs` in
`worktrees/asclepius-geud-gradient`; root `backlog.md` and `checklist.md`.

**Implementation evidence (2026-08-20):** clean lane branch
`fix/asclepius-geud-gradient` is based on `origin/main`
`2f6959b52c36c91169e4f30ad4a7ce8e45d6e901` and publishes one commit,
`390a3ff`. The test evaluates independently perturbed adapter values for every
dose coordinate, uses central differences at two scales with Richardson
extrapolation, and derives truncation plus roundoff bounds from the step and
`f64::EPSILON`. Locked all-target check, full nextest (`20/20`), focused
nextest (`6/6`), Clippy with `-D warnings`, doctests, and Rustdoc pass. A
value-preserving mutation that detaches the adapter input gradient fails four
gradient/value-contract tests, including both independent gradient tests.

The implementation is published as PR
[#24](https://github.com/ryancinsight/asclepius/pull/24) at exact head
`390a3ff60344034a841b0735d9c059231e7f0a8a`, based on merged default
`ce3fea355f0989dcc92a321a1f923f6f30749da4`. PR CI passed at run
`32436064353`; PR #24 is merged. Post-merge default CI passed at
`a38b8b50d1de1d23c08478e4b60d9e7bbd8eacf4` in run `32441333616`; Pages build
`32441332866` remains queued. The dirty primary Asclepius checkout and Atlas
gitlink remain unchanged until Pages and live-page verification are terminal.
The merged lane and remote branch were removed after ancestry verification.

**Ninth pointer batch (2026-08-23, atlas commit to be named):** the Pages
hold cleared — `a38b8b50d1` has terminal `ci` and `pages-build-deployment`
runs at the exact head, and the live site returns HTTP 200 with title
`Asclepius | asclepius`. The Atlas gitlink advances to `a38b8b50d1`;
`recurseml/analysis` remains report-only.


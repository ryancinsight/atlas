//! Manifest-version guard for Atlas member repositories.
//!
//! The Atlas meta-repo coordinates ~25 member repositories. Each member's
//! `Cargo.toml` files carry (a) a workspace release version under
//! `[workspace.package].version`, (b) per-crate versions under
//! `[package].version`, and (c) inline-table dependency entries of the form
//! `dep = { version = "X.Y.Z", path = "...", git = "...", ... }` for every
//! first-party dependency. Because Atlas member repos depend on each other
//! through a shared stack, a silent version regression in any of these
//! surfaces propagates as resolver failure across the entire graph.
//!
//! The motivating incident (recorded in
//! `backlog.md#ATLAS-VERSION-GUARD-001`) was commit `87ab265` on `hermes`,
//! a sed-driven `git` → `path` dep conversion that also reverted the
//! workspace release from `0.5.0` → `0.4.1` and three sibling dev-deps from
//! `0.5.0` → `0.4.0`, all without a declared release intent in the commit
//! message. Origin lied about versions for ~10 hours while integrators
//! failed resolution, and `coeus` stacked 18 commits on the undeliverable
//! base.
//!
//! This crate is the per-member guard that catches that class of mistake at
//! commit time. It is read-only with respect to the repository under audit:
//! it invokes `git diff <range> -- '*.toml'` (or accepts a pre-rendered diff
//! on stdin) and parses version-bearing lines out of the unified diff,
//! classifying each as one of:
//!
//! - [`Direction::Identical`] — the diff re-formatted the version line
//!   without changing the semver. Not a defect.
//! - [`Direction::Forward`] — `X.Y.Z` → `X'.Y'.Z'` with `X'.Y'.Z' > X.Y.Z`.
//!   Defect **unless** the commit message declares a release intent
//!   (`chore(release)`, `build(deps)`, or a `Bump:` / `BREAKING CHANGE:`
//!   footer).
//! - [`Direction::Backward`] — `X.Y.Z` → `X'.Y'.Z'` with `X'.Y'.Z' < X.Y.Z`.
//!   **Always a defect** regardless of declared intent; backward version
//!   movement is quarantine by `git_discipline` policy and the only
//!   remediation is a forward fix.
//!
//! # Exit codes
//!
//! - `0` — clean: every version-bearing diff line is either identical or a
//!   forward bump with declared intent.
//! - `1` — defect detected: at least one backward movement, or a forward
//!   movement without declared intent, or a parse/invariant violation.
//! - `2` — invocation error (bad CLI, missing diff, git plumbing failure).
//!
//! # Library / binary split
//!
//! The library exposes the parser, classifier, and scanner in
//! dependency-free form so it can be reused from a future per-member CI
//! invocation or a meta-level sweep. The binary (`src/main.rs`) is a thin
//! CLI wrapper that pipes git output into the library and renders the
//! report.

#![forbid(unsafe_code)]
#![deny(missing_docs)]

/// Classification of a single version-bearing diff line.
pub mod classify;
/// Typed errors for the guard.
pub mod error;
/// Parsing of `*.toml` and unified diff inputs.
pub mod parse;
/// Report rendering (human / json).
pub mod report;
/// End-to-end diff scan over a member-repo revision range.
pub mod scan;

pub use classify::{Direction, IntentDeclaration, classify_pair};
pub use error::Error;
pub use parse::{VersionLine, parse_diff_line};
pub use report::{Format, Report, render};
pub use scan::{Finding, scan_diff};

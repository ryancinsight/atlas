//! Gitlink coherence auditor for the Atlas meta-repo.
//!
//! The Atlas meta-repo pins ~25 member repositories as git submodules under
//! `repos/<name>`. Each gitlink (the SHA recorded for the submodule entry in
//! the atlas-meta tree) should target a commit that is reachable from the
//! corresponding member repository's `origin/main` branch — otherwise a fresh
//! clone of atlas-meta that initializes submodules receives a SHA that the
//! member's origin never contained, breaking the ADR 0020 gitlink-advance
//! contract.
//!
//! This crate mechanizes the audit pattern documented in
//! `backlog.md#ATLAS-GITLINK-COHERENCE-DEFECT-1`. The audit sequence has now
//! run twice as a manual bash loop, is drift-prone, and has positive
//! maintenance value at PR time — per the `operation` toil-automation policy
//! this is a mechanization candidate.
//!
//! The tool is read-only with respect to the member-repo working trees: it
//! invokes `git merge-base --is-ancestor` and `git rev-parse` through
//! `--git-dir` plumbing and never mutates a peer's checked-out state.
//!
//! # Exit codes
//!
//! - `0` — all probed submodules have gitlinks ancestral to their member
//!   `origin/main` (clean report, possibly with stale-advanceable rows).
//! - `1` — one or more coherence defects detected.
//! - `2` — invocation error (bad CLI, missing `.gitmodules`, git invocation
//!   failure).

#![forbid(unsafe_code)]
#![deny(missing_docs)]

/// Per-repo probe and defect categorization.
pub mod coherence;
/// Typed errors for the auditor.
pub mod error;
/// `.gitmodules` parser.
pub mod gitmodules;
/// Output formatters (human, markdown, json).
pub mod report;

pub use coherence::{Coherence, DefectClass, RepoProbe, audit};
pub use error::Error;
pub use gitmodules::Submodule;

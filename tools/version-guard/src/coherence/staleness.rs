//! Whether the trees the scan reads still represent what the stack publishes.
//!
//! The coherence scan reads checked-in manifests from the members' working
//! trees. A tree that sits behind its own remote reports the version it had,
//! not the version the stack publishes, so every requirement is compared
//! against a stale number. On 2026-09-02 gaia's tree was two commits behind
//! its own 0.4.0 → 0.5.0 bump; the scan compared four consumers against 0.4.0
//! and reported clean while none of them could resolve gaia at all.
//!
//! The audit's premise is that these trees represent the stack. When the
//! premise fails a clean result means less than it appears, so behind trees
//! are named in the report and the clean line says what it is a verdict about.
//! Staleness is not itself a defect: a submodule checkout sits behind its
//! remote by design, because the gitlink pins it there, so failing on it alone
//! would fail every run in CI. Reading a remote-tracking ref is local and
//! offline; keeping it current is the caller's `git fetch`.

use std::path::Path;
use std::process::Command;

use serde::Serialize;

use crate::error::Error;

/// A member whose working tree is behind the branch it tracks.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct StaleMember {
    /// Member path relative to the Atlas root.
    pub member: String,
    /// The remote-tracking branch the tree is measured against.
    pub upstream: String,
    /// Commits present on the upstream branch and absent from the tree.
    pub behind: usize,
}

fn git(repo: &Path, args: &[&str]) -> Result<Option<String>, Error> {
    let output = Command::new("git")
        .arg("--no-pager")
        .arg("-C")
        .arg(repo)
        .args(args)
        .output()?;
    if output.status.success() {
        Ok(Some(
            String::from_utf8_lossy(&output.stdout).trim().to_owned(),
        ))
    } else {
        Ok(None)
    }
}

/// Report every member whose tree is behind its tracked branch.
///
/// A member with no remote-tracking branch — a fresh clone, a repository with
/// no remote — is not stale; there is nothing to be behind of. Only a
/// measurable gap is reported.
///
/// # Errors
///
/// Returns [`Error::Io`](crate::Error::Io) when `git` cannot be executed at
/// all. A member whose individual git query fails is skipped: a repository
/// this scan cannot interrogate is not evidence of staleness.
pub(crate) fn stale_members(
    atlas_root: &Path,
    members: &[&Path],
) -> Result<Vec<StaleMember>, Error> {
    let mut stale = Vec::new();
    for member in members {
        let Some(upstream) = git(
            member,
            &["symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"],
        )?
        else {
            continue;
        };
        if upstream.is_empty() {
            continue;
        }
        let Some(count) = git(
            member,
            &["rev-list", "--count", &format!("HEAD..{upstream}")],
        )?
        else {
            continue;
        };
        let behind: usize = count.parse().unwrap_or(0);
        if behind > 0 {
            stale.push(StaleMember {
                member: member
                    .strip_prefix(atlas_root)
                    .unwrap_or(member)
                    .display()
                    .to_string()
                    .replace('\\', "/"),
                upstream,
                behind,
            });
        }
    }
    Ok(stale)
}

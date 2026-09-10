//! The revision a consumer actually resolves: each member's remote default tip.
//!
//! The working-tree coherence scan reads the manifests a checkout happens to
//! hold. That is the right question for an advance gate, and the wrong one for
//! a scheduled audit: a member resolves a first-party dependency by *name*
//! against that dependency's default branch, never against the gitlink Atlas
//! records. When Moirai's `main` moved 0.5.0 → 0.6.0 on 2026-09-06 every
//! dependent member broke, while the gitlink-pinned scan stayed clean because
//! at those pins the old requirement was still satisfied.
//!
//! This module answers the other question: resolve each member's remote default
//! branch, refresh the remote-tracking ref, and hand back the tip commit. The
//! manifest reader then reads every manifest from that commit's tree, so
//! versions and requirements are compared in the state a consumer resolves.
//!
//! Resolution is deliberately tolerant. A member with no remote, or whose
//! remote cannot be reached, yields `Ok(None)` rather than an error: one
//! unfetchable member must not abort a fleet audit. The caller records such a
//! member as *unmeasured* so a clean verdict is qualified rather than silently
//! narrowed.

use std::path::Path;
use std::process::Command;

use crate::error::Error;

/// Run `git` in `repo`, returning trimmed stdout, or `None` when the command
/// fails. A failed plumbing command is an absent answer, not a defect.
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

/// Ask the remote which branch `HEAD` points at, without relying on any local
/// ref. A submodule cloned with `--depth=1` at a gitlink has no
/// `refs/remotes/origin/HEAD`, which is exactly the state the scheduled audit
/// runs in, so the local symref alone is not enough.
fn remote_default_branch(repo: &Path) -> Option<String> {
    let output = Command::new("git")
        .arg("--no-pager")
        .arg("-C")
        .arg(repo)
        .args(["ls-remote", "--symref", "origin", "HEAD"])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    // The protocol line reads `ref: refs/heads/<branch>\tHEAD`; the target line
    // below it is the commit, which `fetch` will bring down.
    stdout.lines().find_map(|line| {
        line.strip_prefix("ref: refs/heads/")
            .and_then(|rest| rest.split_whitespace().next())
            .map(str::to_owned)
    })
}

/// The default branch name for a member, from the local remote-tracking symref
/// when present, else from the remote itself.
fn default_branch(repo: &Path) -> Result<Option<String>, Error> {
    if let Some(short) = git(
        repo,
        &["symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"],
    )? && !short.is_empty()
    {
        // `origin/<branch>`; the caller re-adds the remote prefix when reading.
        return Ok(Some(short.trim_start_matches("origin/").to_owned()));
    }
    Ok(remote_default_branch(repo))
}

/// Resolve, refresh, and return the commit at a member's remote default tip.
///
/// The remote-tracking ref is fetched first so the tip read is the one the
/// remote publishes now, not the one a stale checkout remembers. A fetch that
/// cannot run — no network, no remote — leaves any existing remote-tracking ref
/// in place, which is still a better answer than the working tree.
///
/// Returns `Ok(None)` when no default branch can be determined or the tip
/// commit cannot be resolved; the caller reports the member as unmeasured.
///
/// # Errors
///
/// Returns [`Error::Io`](crate::Error::Io) when `git` cannot be executed at all.
pub(crate) fn default_tip(member: &Path) -> Result<Option<String>, Error> {
    let Some(branch) = default_branch(member)? else {
        return Ok(None);
    };
    // Best-effort refresh: a fetch failure is not fatal, because a
    // remote-tracking ref from an earlier run still answers the question.
    let _ = git(member, &["fetch", "--quiet", "origin", &branch])?;
    git(
        member,
        &[
            "rev-parse",
            "--verify",
            &format!("origin/{branch}^{{commit}}"),
        ],
    )
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;
    use std::path::PathBuf;

    fn git_ok(repo: &Path, args: &[&str]) {
        let status = Command::new("git")
            .arg("-C")
            .arg(repo)
            .args(["-c", "user.email=guard@atlas.test"])
            .args(["-c", "user.name=Guard Test"])
            .args(args)
            .status()
            .expect("git runs");
        assert!(status.success(), "git {args:?} failed in {repo:?}");
    }

    fn scratch(tag: &str) -> PathBuf {
        let root = std::env::temp_dir().join(format!(
            "version-guard-remote-{tag}-{}-{:?}",
            std::process::id(),
            std::thread::current().id()
        ));
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(&root).unwrap();
        root
    }

    #[test]
    fn default_tip_reads_the_remote_not_the_checkout() {
        // An upstream advances to a second commit while the clone stays on the
        // first -- the gitlink-pinned shape. `default_tip` must fetch and report
        // the remote's tip, not the checkout's HEAD.
        let root = scratch("tip");
        let upstream = root.join("upstream");
        std::fs::create_dir_all(&upstream).unwrap();
        git_ok(&upstream, &["init", "-b", "main"]);
        std::fs::write(
            upstream.join("Cargo.toml"),
            "[package]\nname = \"m\"\nversion = \"0.5.0\"\n",
        )
        .unwrap();
        git_ok(&upstream, &["add", "."]);
        git_ok(&upstream, &["commit", "-m", "0.5.0"]);

        let clone = root.join("clone");
        git_ok(
            &root,
            &[
                "clone",
                "--quiet",
                upstream.to_str().unwrap(),
                clone.to_str().unwrap(),
            ],
        );

        std::fs::write(
            upstream.join("Cargo.toml"),
            "[package]\nname = \"m\"\nversion = \"0.6.0\"\n",
        )
        .unwrap();
        git_ok(&upstream, &["add", "."]);
        git_ok(&upstream, &["commit", "-m", "0.6.0"]);
        let expected = git(&upstream, &["rev-parse", "HEAD"]).unwrap().unwrap();

        let tip = default_tip(&clone).unwrap();
        assert_eq!(
            tip.as_deref(),
            Some(expected.as_str()),
            "the remote tip must be reported, not the behind checkout"
        );

        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn a_repository_without_a_remote_is_unmeasured_not_an_error() {
        let root = scratch("noremote");
        let repo = root.join("repo");
        std::fs::create_dir_all(&repo).unwrap();
        git_ok(&repo, &["init", "-b", "main"]);
        assert_eq!(default_tip(&repo).unwrap(), None);
        let _ = std::fs::remove_dir_all(&root);
    }
}

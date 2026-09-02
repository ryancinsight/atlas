//! Tests for the working-tree freshness precondition.
//!
//! These build real repositories: the property under test is what `git`
//! reports about a tree and its remote-tracking branch, and a hand-written
//! fixture would assert the test's model of git rather than git's behaviour.

use std::path::{Path, PathBuf};
use std::process::Command;

use super::staleness::stale_members;

fn git(repo: &Path, args: &[&str]) -> bool {
    Command::new("git")
        .arg("-C")
        .arg(repo)
        .arg("-c")
        .arg("user.email=guard@atlas.test")
        .arg("-c")
        .arg("user.name=Guard Test")
        .arg("-c")
        .arg("commit.gpgsign=false")
        .args(args)
        .output()
        .is_ok_and(|out| out.status.success())
}

fn scratch(name: &str) -> PathBuf {
    let root = std::env::temp_dir().join(format!(
        "atlas-staleness-{name}-{}-{:?}",
        std::process::id(),
        std::thread::current().id()
    ));
    let _ = std::fs::remove_dir_all(&root);
    std::fs::create_dir_all(&root).expect("scratch root");
    root
}

fn commit(repo: &Path, file: &str, body: &str) {
    std::fs::write(repo.join(file), body).expect("write");
    assert!(git(repo, &["add", "."]), "git add");
    assert!(git(repo, &["commit", "-m", file]), "git commit");
}

/// A clone that has fetched a commit it does not hold is behind by exactly
/// that many commits, which is the case the scan must refuse to measure.
#[test]
fn a_tree_behind_its_upstream_is_reported() {
    let root = scratch("behind");
    let upstream = root.join("upstream");
    std::fs::create_dir_all(&upstream).expect("upstream dir");
    assert!(git(&upstream, &["init", "-b", "main"]), "git init");
    commit(&upstream, "first.txt", "one\n");

    let member = root.join("repos").join("member");
    std::fs::create_dir_all(root.join("repos")).expect("repos dir");
    assert!(
        Command::new("git")
            .arg("clone")
            .arg("--quiet")
            .arg(&upstream)
            .arg(&member)
            .output()
            .is_ok_and(|out| out.status.success()),
        "git clone"
    );

    commit(&upstream, "second.txt", "two\n");
    assert!(git(&member, &["fetch", "--quiet", "origin"]), "git fetch");

    let stale = stale_members(&root, &[member.as_path()]).expect("scan");
    assert_eq!(stale.len(), 1, "one member is behind: {stale:?}");
    assert_eq!(stale[0].behind, 1);
    assert_eq!(stale[0].member, "repos/member");
    assert!(stale[0].upstream.ends_with("main"), "{}", stale[0].upstream);

    let _ = std::fs::remove_dir_all(&root);
}

/// A tree holding everything its upstream holds is not behind, so a stack
/// that has been synchronised measures clean rather than permanently
/// unmeasured.
#[test]
fn a_tree_level_with_its_upstream_is_not_reported() {
    let root = scratch("level");
    let upstream = root.join("upstream");
    std::fs::create_dir_all(&upstream).expect("upstream dir");
    assert!(git(&upstream, &["init", "-b", "main"]), "git init");
    commit(&upstream, "first.txt", "one\n");

    let member = root.join("repos").join("member");
    std::fs::create_dir_all(root.join("repos")).expect("repos dir");
    assert!(
        Command::new("git")
            .arg("clone")
            .arg("--quiet")
            .arg(&upstream)
            .arg(&member)
            .output()
            .is_ok_and(|out| out.status.success()),
        "git clone"
    );

    let stale = stale_members(&root, &[member.as_path()]).expect("scan");
    assert!(stale.is_empty(), "level tree reported stale: {stale:?}");

    let _ = std::fs::remove_dir_all(&root);
}

/// A directory git cannot interrogate — no repository, no remote — is not
/// evidence of staleness, and must not turn every scan into a defect.
#[test]
fn a_directory_without_a_tracking_branch_is_not_reported() {
    let root = scratch("bare");
    let member = root.join("repos").join("member");
    std::fs::create_dir_all(&member).expect("member dir");
    assert!(
        stale_members(&root, &[member.as_path()])
            .expect("scan")
            .is_empty(),
        "a non-repository was reported stale"
    );

    let solo = root.join("repos").join("solo");
    std::fs::create_dir_all(&solo).expect("solo dir");
    assert!(git(&solo, &["init", "-b", "main"]), "git init");
    commit(&solo, "first.txt", "one\n");
    assert!(
        stale_members(&root, &[solo.as_path()])
            .expect("scan")
            .is_empty(),
        "a repository with no remote was reported stale"
    );

    let _ = std::fs::remove_dir_all(&root);
}

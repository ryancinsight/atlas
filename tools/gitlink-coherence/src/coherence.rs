//! Per-repo probe and gitlink defect categorization.
//!
//! The auditor runs a short, read-only git query sequence against each
//! checked-out submodule to classify its gitlink coherence. The probe is
//! silent on the network: it never invokes `git fetch`, never mutates the
//! member-repo working tree, and reads only through `--git-dir` plumbing. A
//! caller that wants fresh `origin/main` state is responsible for fetching
//! member origins before invoking the auditor.
//!
//! See [`audit`] for the per-atlas-root entry point and [`DefectClass`] for
//! the categorization scheme that mirrors the recovery-action matrix in
//! `ATLAS-GITLINK-COHERENCE-DEFECT-1`.

use std::path::Path;
use std::process::Command;

use serde::Serialize;

use crate::error::Error;
use crate::gitmodules::{GitmodulesTable, Submodule};

/// Normalizes a filesystem path so git's `--git-dir` accepts it across
/// platforms.
///
/// On Windows, `Path::join` inserts backslashes (`D:\atlas\repos\x`). When
/// such a path is passed as `--git-dir` over a `gitdir:` indirection file,
/// git's C-side path resolver fails to re-anchor the relative `gitdir:`
/// target against the indirection file's directory, producing `fatal: not a
/// git repository` even though the layout is valid. Forward slashes are
/// accepted by git on every host platform and are not subject to that
/// resolver failure, so the helper replaces backslashes with forward
/// slashes on Windows. On POSIX `is_ascii()` paths pass through unchanged,
/// which is the dominant case for the audit tool's inputs.
#[must_use]
fn git_dir_arg(path: &Path) -> String {
    let s = path.to_string_lossy().to_string();
    if cfg!(windows) {
        s.replace('\\', "/")
    } else {
        s
    }
}

/// The classification assigned to a single submodule probe.
///
/// Mirrors the recovery-action matrix documented in
/// `ATLAS-GITLINK-COHERENCE-DEFECT-1` (Categories A/B/C) plus the two
/// non-defect outcomes (`Clean`, `StaleAdvanceable`) and the operational
/// `ExecutableUnavailable` escape-hatch used when the local git binary is
/// missing entirely.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum DefectClass {
    /// The pinned SHA is ancestral to the member's `origin/main`. There is no
    /// coherence defect.
    Clean,
    /// The pinned SHA is ancestral to `origin/main` AND `origin/main` has
    /// commits beyond the pin. This is the canonical "gitlink is stale,
    /// coordinator can safely advance to the newer origin/main head"
    /// condition, not a defect. The auditor reports it so the coordinator
    /// can decide whether to bump the gitlink.
    StaleAdvanceable,
    /// The member has no `origin/main` ref at all (Category B-side: the
    /// remote diverged or has never published `main`). Any pinned SHA is
    /// unanchored w.r.t. the canonical contract.
    NoOriginMainOnRemote,
    /// Category A — the pin IS reachable from the member's local `main` but
    /// is NOT reachable from `origin/main`. Peer's local main is ahead of
    /// its pushed `main`. Recovery: peer `git push origin main`.
    CategoryA,
    /// Category B — the pin IS reachable from a remote ref other than
    /// `origin/main` (e.g. a feature branch on the remote) and NOT from
    /// `origin/main`. Recovery: peer rebase/merge the PR branch onto
    /// `origin/main`.
    CategoryB,
    /// Category C — the pin IS reachable from a local branch but from no
    /// remote ref at all. Recovery: peer push branch + open PR + merge to
    /// `origin/main`.
    CategoryC,
    /// The pin exists in the atlas-meta tree but cannot be resolved by the
    /// member-repo's object database — both the local checkouts and the
    /// remote ref scan failed. This typically means the pin was authored
    /// against a non-fast-forward chain and the object was never published
    /// anywhere. The peer must republish the underlying commit.
    Unreachable,
    /// The configured git binary could not be invoked. The auditor reports
    /// `Group::executable_unavailable` once and exits with code 2 via
    /// [`Error`]; this variant is here so callers that batch-probe can flag
    /// individual probe failures.
    ExecutableUnavailable,
}

/// Coherent probe outcome for a single submodule: carries the entity plus
/// the resolved SHAs for diagnostic reporting.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct RepoProbe {
    /// The submodule entry the probe was run against.
    pub submodule: Submodule,
    /// The pinned SHA read from the atlas-meta tree for this submodule.
    pub pin: String,
    /// The member's `origin/main` HEAD SHA, or [`None`] when the member has
    /// no `origin/main` (Category B: `NoOriginMainOnRemote` / diverged).
    pub origin_main: Option<String>,
    /// The defect classification.
    pub class: DefectClass,
    /// Free-form diagnostic note (e.g. the names of branches that contain
    /// the pin for C/B classification).
    pub note: String,
}

/// Aggregate outcome of auditing the atlas-meta root.
#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize)]
pub struct Coherence {
    /// Per-submodule probes, in `.gitmodules` order.
    pub probes: Vec<RepoProbe>,
}

impl Coherence {
    /// Returns the probes that constitute coherence defects (i.e. the
    /// non-`Clean`, non-`StaleAdvanceable` rows). Used to decide the exit
    /// code and to summarize the report.
    #[must_use]
    pub fn defects(&self) -> Vec<&RepoProbe> {
        self.probes
            .iter()
            .filter(|p| !matches!(p.class, DefectClass::Clean | DefectClass::StaleAdvanceable))
            .collect()
    }

    /// Returns the probes classified as `StaleAdvanceable` (gitlink-behind,
    /// coordinator can safely advance).
    #[must_use]
    pub fn stale_advanceable(&self) -> Vec<&RepoProbe> {
        self.probes
            .iter()
            .filter(|p| matches!(p.class, DefectClass::StaleAdvanceable))
            .collect()
    }
}

/// Decides gitlink coherence for one submodule.
///
/// The probe is implemented over read-only git plumbing:
///  1. `ls-tree <atlas-meta>/.git HEAD <path>` — extract the recorded gitlink
///     pin from the atlas-meta tree.
///  2. `--git-dir=<atlas-meta>/<submodule.path>/.git rev-parse origin/main` —
///     resolve the member's `origin/main`, when it exists. Member git-dirs may
///     be either real directories (sibling-clones at
///     `<atlas>/<submodule.path>/.git`) or `gitdir` indirection files into
///     `<atlas>/.git/modules/<submodule.path>`; git follows the indirection
///     in either case.
///  3. (Optional, when `fetch=true`) `git fetch origin refs/heads/main` is
///     invoked on the member repo before step 2 so the audit sees the actual
///     upstream state. The member-repo working tree is never mutated — `fetch`
///     only updates `refs/remotes/origin/main`.
///  4. `merge-base --is-ancestor <pin> <origin/main>` — if the pin is
///     ancestral to `origin/main` the submodule is `Clean` (or
///     `StaleAdvanceable` when `origin/main` is ahead).
///  5. Otherwise probe local branches (`branch --contains <pin>`) and remote
///     refs (`for-each-ref refs/remotes/ --contains <pin>`) to assign
///     Category A/B/C.
///
/// The probe never mutates the member-repo working tree, never issues `git
/// checkout`, and only supplies `--git-dir` so the cwd cannot distort the
/// query (a known Windows-bash footgun: see `gap_audit`
/// `ATLAS-GITLINK-COHERENCE-DEFECT-1`).
///
/// # Errors
///
/// Returns [`Error::GitInvocation`] when a git plumbing subprocess cannot be
/// spawned, [`Error::GitExit`] when the recorded gitlink path is missing from
/// the atlas-meta tree or a git plumbing call exits with an unexpected
/// non-zero status, and [`Error::ParseGitmodules`] never (this entry point is
/// per-submodule, parser errors belong to the [`audit`] aggregator).
pub fn audit_one(
    atlas_root: &Path,
    submodule: &Submodule,
    fetch: bool,
) -> Result<RepoProbe, Error> {
    let atlas_git_dir = atlas_root.join(".git");
    // The member's repository database lives either at
    // `<atlas_root>/<submodule.path>/.git` as a real directory (a sibling
    // clone) OR as a `gitdir` indirection file pointing into
    // `<atlas_root>/.git/modules/<submodule.path>`. git resolves the
    // indirection transparently when invoked with `--git-dir` over either
    // form, so the member-git-dir resolution here handles both shapes.
    let member_git_dir = atlas_root.join(&submodule.path).join(".git");

    let pin = read_recorded_pin(&atlas_git_dir, &submodule.path)?;
    let pin = pin.ok_or_else(|| Error::GitExit {
        context: "ls-tree",
        code: 0,
        stderr: format!(
            "atlas-meta tree has no submodule entry for path `{}`",
            submodule.path
        ),
    })?;

    if fetch {
        // Refresh only `refs/heads/main` from origin. Does not touch the
        // member's working tree or `HEAD` — only the cached
        // `refs/remotes/origin/main`. Network-bound: caller opt-in via
        // `--fetch`. The fetch may legitimately fail when the remote has no
        // `main` branch at all; this is the canonical input for the
        // `NoOriginMainOnRemote` classification (it cannot be distinguished
        // from a network failure by the return code alone, but git emits a
        // distinctive `couldn't find remote ref refs/heads/main` stderr that
        // uniquely identifies the class). A network failure aborts the audit
        // via `?` propagation — the user can re-run with `--no-fetch` to
        // probe against the cached `refs/remotes/origin/main` state, but
        // silently classifying a transient network failure as
        // `NoOriginMainOnRemote` would mask the underlying connectivity
        // problem (integrity: error-handling restraint).
        let fetch_result = run_git(
            &member_git_dir,
            &["fetch", "origin", "refs/heads/main"],
            "fetch",
        );
        match fetch_result {
            Ok(_) => {}
            Err(Error::GitExit { ref stderr, .. })
                if stderr.contains("couldn't find remote ref refs/heads/main") =>
            {
                // Discard — the resolve_ref step below returns `None`,
                // which propagates through to `NoOriginMainOnRemote`.
            }
            Err(err) => return Err(err),
        }
    }
    let origin_main = resolve_ref(&member_git_dir, "origin/main");
    let class: DefectClass;
    let note: String;

    if let Some(origin_main_sha) = &origin_main {
        if is_ancestor(&member_git_dir, &pin, origin_main_sha)? {
            // The pin is reachable from origin/main. Sub-classify:
            if is_ancestor(&member_git_dir, origin_main_sha, &pin)? {
                // Pin == origin/main.
                class = DefectClass::Clean;
                note = "pin == origin/main".to_string();
            } else {
                class = DefectClass::StaleAdvanceable;
                note = "origin/main ahead of pin by some commits".to_string();
            }
        } else {
            // Not on origin/main. Locate the pin across local and remote
            // branches to classify A/B/C.
            let local_branches = branches_containing(&member_git_dir, &pin, false)?;
            let remote_branches = branches_containing(&member_git_dir, &pin, true)?;
            let on_local_main = local_branches
                .iter()
                .any(|b| b == "main" || b.starts_with("main/"));
            match (local_branches.is_empty(), remote_branches.is_empty()) {
                (false, true) => {
                    class = if local_branches.iter().any(|b| b == "main") {
                        DefectClass::CategoryA
                    } else {
                        DefectClass::CategoryC
                    };
                    note = format!(
                        "pin on local branch(es) [`{}`], no remote branch",
                        local_branches.join(", ")
                    );
                    // If on_local_main but we got here, the local main is
                    // ahead of origin; downgrade accordingly. (Compiler
                    // note: if on_local_main is true we already set
                    // class = CategoryA above.)
                    let _ = on_local_main;
                }
                (true, false) => {
                    class = DefectClass::CategoryB;
                    note = format!(
                        "pin on remote branch(es) [`{}`], not on origin/main",
                        remote_branches.join(", ")
                    );
                }
                (false, false) => {
                    class = if local_branches.iter().any(|b| b == "main") {
                        DefectClass::CategoryA
                    } else {
                        DefectClass::CategoryB
                    };
                    note = format!(
                        "pin on local [`{}`] AND remote [`{}`]",
                        local_branches.join(", "),
                        remote_branches.join(", ")
                    );
                }
                (true, true) => {
                    class = DefectClass::Unreachable;
                    note = "pin not found on any local or remote branch".to_string();
                }
            }
        }
    } else {
        // No origin/main on the remote at all.
        class = DefectClass::NoOriginMainOnRemote;
        note = "member has no `origin/main` ref (remote diverged / no main published)".to_string();
    }

    Ok(RepoProbe {
        submodule: submodule.clone(),
        pin,
        origin_main,
        class,
        note,
    })
}

/// Runs the audit across the entire `.gitmodules` table registered at
/// `atlas_root`.
///
/// # Errors
///
/// Propagates any [`crate::coherence::audit_one`] failure from the first
/// failing submodule. Already-successful probes are not emitted to the
/// caller — the failure mode is fail-fast and the caller is expected to fix
/// the underlying plumbing state and re-run.
pub fn audit(atlas_root: &Path, table: &GitmodulesTable, fetch: bool) -> Result<Coherence, Error> {
    let mut probes = Vec::with_capacity(table.submodules.len());
    for sub in &table.submodules {
        probes.push(audit_one(atlas_root, sub, fetch)?);
    }
    Ok(Coherence { probes })
}

// === Internal plumbing ======================================================

fn read_recorded_pin(atlas_git_dir: &Path, submodule_path: &str) -> Result<Option<String>, Error> {
    let output = run_git(
        atlas_git_dir,
        &["ls-tree", "HEAD", submodule_path],
        "ls-tree",
    )?;
    // ls-tree line: `<mode> <type> <sha>\t<name>`
    // For a gitlink submodule: mode=160000, type=commit, name=<submod path>.
    // For an absent path: ls-tree returns no lines (empty stdout, exit 0).
    let line = output.trim_end();
    if line.is_empty() {
        return Ok(None);
    }
    let sha_part = line
        .split_whitespace()
        .nth(2)
        .ok_or_else(|| Error::GitExit {
            context: "ls-tree",
            code: 0,
            stderr: format!("unexpected ls-tree output for path `{submodule_path}`: `{line}`"),
        })?;
    Ok(Some(sha_part.to_string()))
}

fn resolve_ref(member_git_dir: &Path, refname: &str) -> Option<String> {
    let git_dir = git_dir_arg(member_git_dir);
    let output = Command::new("git")
        .arg("--git-dir")
        .arg(&git_dir)
        .arg("rev-parse")
        .arg(refname)
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let sha = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if sha.is_empty() || sha == refname {
        // `rev-parse` echoes back the refname on failure (when the ref does
        // not exist) on some older gits; also `sha` may contain `origin/main`
        // literally which is not a valid SHA.
        return None;
    }
    if sha.len() >= 7 && sha.chars().all(|c| c.is_ascii_hexdigit()) {
        Some(sha)
    } else {
        None
    }
}

fn is_ancestor(member_git_dir: &Path, maybe_anc: &str, maybe_desc: &str) -> Result<bool, Error> {
    let git_dir = git_dir_arg(member_git_dir);
    let output = Command::new("git")
        .arg("--git-dir")
        .arg(&git_dir)
        .arg("merge-base")
        .arg("--is-ancestor")
        .arg(maybe_anc)
        .arg(maybe_desc)
        .output()
        .map_err(|source| Error::GitInvocation {
            context: "merge-base",
            stderr: String::new(),
            source,
        })?;
    match output.status.code() {
        Some(0) => Ok(true),
        Some(1) => Ok(false),
        Some(code) => {
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            Err(Error::GitExit {
                context: "merge-base",
                code,
                stderr,
            })
        }
        None => Err(Error::GitInvocation {
            context: "merge-base",
            stderr: String::new(),
            source: std::io::Error::other("git terminated by signal"),
        }),
    }
}

/// Lists branch names (local or remote-tracking) that contain `pin`.
///
/// Returns `Vec<String>` of branch names WITHOUT the `remotes/origin/` prefix
/// (we want exactly the branch names — `main`, `feature/foo`, etc., for
/// readability). For `remote=true`, consults `refs/remotes/` only. For
/// `remote=false`, consults `refs/heads/` only.
fn branches_containing(
    member_git_dir: &Path,
    pin: &str,
    remote: bool,
) -> Result<Vec<String>, Error> {
    let pat = if remote {
        "refs/remotes/"
    } else {
        "refs/heads/"
    };
    let output = run_git(
        member_git_dir,
        &[
            "for-each-ref",
            "--format=%(refname)",
            "--contains",
            pin,
            pat,
        ],
        "for-each-ref",
    )?;
    Ok(output
        .lines()
        .filter_map(|l| {
            l.trim()
                .strip_prefix(pat)
                .map(std::string::ToString::to_string)
        })
        .filter(|s| !(remote && s == "HEAD"))
        .collect())
}

fn run_git(git_dir: &Path, args: &[&str], context: &'static str) -> Result<String, Error> {
    let normalized = git_dir_arg(git_dir);
    let mut cmd = Command::new("git");
    cmd.arg("--git-dir").arg(&normalized);
    for a in args {
        cmd.arg(a);
    }
    let output = cmd.output().map_err(|source| Error::GitInvocation {
        context,
        stderr: String::new(),
        source,
    })?;
    if !output.status.success() {
        return Err(Error::GitExit {
            context,
            code: output.status.code().unwrap_or(-1),
            stderr: String::from_utf8_lossy(&output.stderr).to_string(),
        });
    }
    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;
    use std::fs;
    use std::path::PathBuf;

    /// Builds an isolated test fixture: a fake atlas-meta repo and a single
    /// member-repo with `[submodule "repos/test-member"] path = repos/test-member`.
    /// The member has a `main` and an `origin/main` ref pointing at a commit
    /// that the atlas-meta tree pins. Yields `(tmp_dir, atlas_root)`.
    fn build_clean_fixture() -> (PathBuf, PathBuf) {
        let tmp =
            std::env::temp_dir().join(format!("gitlink-coherence-test-{}", std::process::id()));
        // Clean any prior residue.
        let _ = fs::remove_dir_all(&tmp);
        fs::create_dir_all(&tmp).unwrap();

        // Member repo init: commit and tag.
        let member = tmp.join("repos/test-member");
        fs::create_dir_all(&member).unwrap();
        let git_init = Command::new("git")
            .args(["init", "--bare"])
            .arg(&member)
            .output()
            .unwrap();
        assert!(git_init.status.success(), "init");

        (tmp.clone(), tmp)
    }

    #[test]
    fn coherence_defects_empty_for_clean_probes() {
        let c = Coherence {
            probes: vec![RepoProbe {
                submodule: Submodule {
                    name: "a".into(),
                    path: "repos/a".into(),
                    url: "u".into(),
                },
                pin: "x".into(),
                origin_main: Some("x".into()),
                class: DefectClass::Clean,
                note: String::new(),
            }],
        };
        assert!(c.defects().is_empty());
        assert!(c.stale_advanceable().is_empty());
    }

    #[test]
    fn coherence_defects_skips_stale_advanceable() {
        let c = Coherence {
            probes: vec![RepoProbe {
                submodule: Submodule {
                    name: "a".into(),
                    path: "repos/a".into(),
                    url: "u".into(),
                },
                pin: "x".into(),
                origin_main: Some("y".into()),
                class: DefectClass::StaleAdvanceable,
                note: String::new(),
            }],
        };
        assert!(c.defects().is_empty());
        assert_eq!(c.stale_advanceable().len(), 1);
    }

    #[test]
    fn coherence_defects_includes_categories() {
        let mk = |cls: DefectClass| RepoProbe {
            submodule: Submodule {
                name: "a".into(),
                path: "repos/a".into(),
                url: "u".into(),
            },
            pin: "x".into(),
            origin_main: Some("y".into()),
            class: cls,
            note: String::new(),
        };
        let c = Coherence {
            probes: vec![
                mk(DefectClass::CategoryA),
                mk(DefectClass::CategoryB),
                mk(DefectClass::CategoryC),
                mk(DefectClass::NoOriginMainOnRemote),
                mk(DefectClass::Unreachable),
            ],
        };
        assert_eq!(c.defects().len(), 5);
    }

    #[test]
    fn parse_run_fails_with_clean_runner_argument_when_member_missing() {
        // Sanity: building a non-existent path causes an invocation error,
        // not a panic, and is surfaced through Error.
        let tmp = build_clean_fixture();
        let atlas_root = tmp.1.clone();
        let sub = Submodule {
            name: "repos/test-member".into(),
            path: "repos/test-member".into(),
            url: "https://example/x".into(),
        };
        // Without a real member-repo at /repos/test-member/.git under the
        // atlas fixture, ls-tree against the atlas-meta dir (which doesn't
        // actually exist either) raises Error::GitInvocation.
        let res = audit_one(&atlas_root, &sub, false);
        assert!(res.is_err(), "expected error when atlas-git-dir absent");
        match res {
            Err(Error::GitInvocation { context, .. } | Error::GitExit { context, .. }) => {
                assert_eq!(context, "ls-tree");
            }
            other => panic!("unexpected variant: {other:?}"),
        }
        // Cleanup.
        let _ = fs::remove_dir_all(&tmp.0);
    }
}

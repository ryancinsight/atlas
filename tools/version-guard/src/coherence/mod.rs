//! Stack-wide first-party dependency/version coherence checking.
//!
//! The coherence scan deliberately reads checked-in manifests instead of
//! invoking Cargo or contacting a registry. The Atlas meta-repository's
//! `.gitmodules` file defines the allowlist, while package manifests define
//! the current first-party package versions. This keeps the check deterministic
//! and makes those files the single sources of truth.
//!
//! Reading trees rather than remotes has one precondition: the trees must be
//! current. A member behind its own remote carries the version it had, not the
//! version the stack publishes, so the scan reports such members and declines
//! to call the result clean.

mod manifest;
mod member;
mod remote;
mod requirement;
mod staleness;
#[cfg(test)]
#[path = "staleness_tests.rs"]
mod staleness_tests;
mod toml;

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::process::Command;

use serde::Serialize;

use crate::error::Error;
use crate::report::Format;

use manifest::{
    ParsedManifest, dependency_specs, package_index, parse_manifest, parse_manifest_content,
    workspace_dependency_index,
};
use member::{
    UnreadableDir, collect_manifests, is_first_party_source, is_first_party_source_in_tree,
    registered_members, remote_manifest_paths,
};
use requirement::matches_requirement;
pub use staleness::StaleMember;
use staleness::stale_members;

/// Which state of the stack a coherence scan measures.
///
/// The two answer different questions and neither subsumes the other.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum View {
    /// The manifests as they sit on disk. This is the advance gate: it reports
    /// whether the recorded stack is internally consistent at the revisions
    /// Atlas pins.
    Worktree,
    /// The manifests as published at each member's remote default tip. This is
    /// the scheduled audit: a member resolves a first-party dependency by name
    /// against that dependency's default branch, so this is the state consumers
    /// actually resolve, and the state that broke when a provider bumped
    /// without its consumer sweep.
    Remotes,
}

/// One first-party requirement that does not accept the current package version.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct CoherenceFinding {
    /// Registered repository containing the consumer manifest.
    pub consumer: String,
    /// Manifest path relative to the Atlas root.
    pub manifest: String,
    /// Dependency key as written by the consumer.
    pub dependency: String,
    /// Resolved first-party package name (`package =` aliases included).
    pub package: String,
    /// Cargo requirement copied from the manifest or workspace dependency.
    pub required: String,
    /// Current version found in the allowlisted package index.
    pub actual: String,
    /// Short explanation of the mismatch.
    pub reason: String,
}

/// Result of a deterministic stack-coherence scan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CoherenceReport {
    /// Number of package manifests inspected.
    pub manifest_count: usize,
    /// Number of uniquely named first-party packages indexed.
    pub package_count: usize,
    /// Number of first-party requirements carrying a version constraint.
    pub requirement_count: usize,
    /// Version requirement mismatches.
    pub findings: Vec<CoherenceFinding>,
    /// Members whose working tree is behind the branch it tracks. Their
    /// manifests describe an older state than the stack publishes, so any
    /// verdict about them — clean included — is measured against versions
    /// that are not what the stack has.
    pub stale: Vec<StaleMember>,
    /// Directories the walk could not read, and so did not measure. Empty in
    /// the ordinary case; a non-empty list means some tree went unscanned.
    pub unscanned: Vec<UnreadableDir>,
    /// Members whose remote default tip could not be resolved while measuring
    /// [`View::Remotes`], so their published manifests went unmeasured. Always
    /// empty for [`View::Worktree`], which needs no remote.
    pub unmeasured: Vec<String>,
}

impl CoherenceReport {
    /// Render the report using the version guard's human or JSON format.
    #[must_use]
    pub fn render(&self, format: Format) -> String {
        match format {
            Format::Human => self.render_human(),
            Format::Json => self.render_json(),
        }
    }

    /// Return whether at least one coherence mismatch exists.
    ///
    /// Stale trees are reported but do not make a defect on their own. A
    /// submodule checkout legitimately sits behind its remote — the gitlink
    /// pins it there — so failing on that alone would fail every run. What
    /// staleness changes is the meaning of a clean result, which the rendered
    /// report says outright rather than leaving to the reader.
    #[must_use]
    pub const fn has_defect(&self) -> bool {
        !self.findings.is_empty()
    }

    fn render_human(&self) -> String {
        let mut out = format!(
            "version-guard coherence: {} manifests, {} packages, {} first-party requirements\n",
            self.manifest_count, self.package_count, self.requirement_count
        );
        for stale in &self.stale {
            let _ = writeln!(
                out,
                "{}: tree is {} commit(s) behind {}; its manifests are not what the stack publishes",
                stale.member, stale.behind, stale.upstream
            );
        }
        for skipped in &self.unscanned {
            let _ = writeln!(
                out,
                "{}: directory not read ({}); any manifest beneath it went unmeasured",
                skipped.path.display(),
                skipped.reason
            );
        }
        for member in &self.unmeasured {
            let _ = writeln!(
                out,
                "{member}: no remote default tip could be resolved; its published manifests went unmeasured"
            );
        }
        if self.findings.is_empty()
            && self.stale.is_empty()
            && self.unscanned.is_empty()
            && self.unmeasured.is_empty()
        {
            out.push_str("version-guard coherence: clean\n");
        } else if self.findings.is_empty() {
            let _ = writeln!(
                out,
                "version-guard coherence: no mismatch among the trees as checked out; {} of them are behind, {} director(ies) went unread, and {} member(s) were unmeasured, so this is not a verdict about what the stack publishes",
                self.stale.len(),
                self.unscanned.len(),
                self.unmeasured.len()
            );
        } else {
            for finding in &self.findings {
                let _ = writeln!(
                    out,
                    "{}: {} requires {} {}, actual {} ({})",
                    finding.manifest,
                    finding.dependency,
                    finding.package,
                    finding.required,
                    finding.actual,
                    finding.reason
                );
            }
            out.push_str("version-guard coherence: DEFECT\n");
        }
        out
    }

    fn render_json(&self) -> String {
        #[derive(Serialize)]
        struct View<'a> {
            manifest_count: usize,
            package_count: usize,
            requirement_count: usize,
            defect_count: usize,
            findings: &'a [CoherenceFinding],
            stale: &'a [StaleMember],
            unscanned: &'a [UnreadableDir],
            unmeasured: &'a [String],
        }
        let view = View {
            manifest_count: self.manifest_count,
            package_count: self.package_count,
            requirement_count: self.requirement_count,
            defect_count: self.findings.len(),
            findings: &self.findings,
            stale: &self.stale,
            unscanned: &self.unscanned,
            unmeasured: &self.unmeasured,
        };
        serde_json::to_string(&view)
            .unwrap_or_else(|_| String::from("{\"error\":\"serialization failed\"}"))
    }
}

/// Scan first-party manifests under registered Atlas members and report every
/// requirement the current stack does not satisfy.
///
/// `view` selects which state of the stack is measured; see [`View`]. The scan
/// is read-only with respect to the members' histories. A requirement is
/// checked only when its dependency key or explicit `package =` target names an
/// indexed first-party package, the dependency names a first-party source (a
/// `path` or `git` target, so a same-named third-party crate is not confused
/// with a member), and the requirement contains a `version =` value. Path-only
/// dependencies are valid Cargo declarations but carry no version assertion for
/// this particular guard to evaluate.
///
/// # Errors
///
/// Returns [`Error::Manifest`] when the member index, a member directory, or a
/// checked-in manifest cannot be read, and [`Error::Git`] when a member's tree
/// cannot be listed in [`View::Remotes`].
pub fn scan_atlas(atlas_root: &Path, view: View) -> Result<CoherenceReport, Error> {
    let members = registered_members(atlas_root)?;
    let mut unscanned: Vec<UnreadableDir> = Vec::new();
    let mut manifests: Vec<PathBuf> = Vec::new();
    let mut unmeasured: Vec<String> = Vec::new();
    let mut stale: Vec<StaleMember> = Vec::new();
    // Names, per member root, the commit whose tree the manifest reader must use
    // instead of the working tree.
    let origin_ref_of: BTreeMap<PathBuf, String> = match view {
        View::Worktree => {
            for member in &members {
                let root_manifest = member.path.join("Cargo.toml");
                if !root_manifest.is_file() {
                    return Err(Error::Manifest {
                        path: root_manifest.display().to_string(),
                        message: String::from("registered member has no Cargo.toml"),
                    });
                }
                collect_manifests(&member.path, &mut manifests, &mut unscanned)?;
            }
            // A behind member's working tree holds the version it had, not the
            // version the stack publishes, so every requirement compared against
            // it is measured against a stale number (the gaia 0.4.0 → 0.5.0
            // case). Read such a member's manifests at its origin tip instead,
            // so the verdict describes what a consumer would resolve.
            let paths: Vec<&Path> = members.iter().map(|member| member.path.as_path()).collect();
            stale = stale_members(atlas_root, &paths)?;
            stale
                .iter()
                .filter_map(|entry| {
                    let member_path = atlas_root.join(&entry.member);
                    let commit = entry.upstream_commit.as_ref()?;
                    Some((member_path, commit.clone()))
                })
                .collect()
        }
        View::Remotes => {
            let mut refs = BTreeMap::new();
            for member in &members {
                match remote::default_tip(&member.path)? {
                    Some(commit) => {
                        manifests.extend(remote_manifest_paths(member, &commit)?);
                        refs.insert(member.path.clone(), commit);
                    }
                    // A member whose remote cannot be resolved is not evidence
                    // of coherence. Name it so a clean verdict is qualified.
                    None => unmeasured.push(display_member(atlas_root, &member.path)),
                }
            }
            refs
        }
    };

    let parsed = manifests
        .iter()
        .map(|path| read_manifest(path, atlas_root, &origin_ref_of))
        .collect::<Result<Vec<_>, _>>()?;
    let packages = package_index(&parsed)?;
    let workspace_deps = workspace_dependency_index(&parsed);
    let mut findings = Vec::new();
    let mut requirement_count = 0;

    for manifest in &parsed {
        for dependency in dependency_specs(manifest, &workspace_deps) {
            let package_name = dependency
                .package
                .clone()
                .unwrap_or_else(|| dependency.key.clone());
            let Some(package) = packages.get(&package_name) else {
                continue;
            };
            let first_party = match view {
                View::Worktree => {
                    is_first_party_source(manifest, &dependency, &members, atlas_root)
                }
                // The tree view cannot canonicalize a path that is newer than
                // the checkout, so it confirms membership lexically instead.
                View::Remotes => is_first_party_source_in_tree(manifest, &dependency, &members),
            };
            if !first_party {
                continue;
            }
            let Some(required) = dependency.version.as_deref() else {
                continue;
            };
            requirement_count += 1;
            if !matches_requirement(required, &package.version) {
                findings.push(CoherenceFinding {
                    consumer: manifest.consumer.clone(),
                    manifest: manifest.display_path.clone(),
                    dependency: dependency.key,
                    package: package_name.clone(),
                    required: required.to_string(),
                    actual: package.version.clone(),
                    reason: String::from("requirement does not accept current package version"),
                });
            }
        }
    }

    Ok(CoherenceReport {
        manifest_count: parsed.len(),
        package_count: packages.len(),
        requirement_count,
        findings,
        stale,
        unscanned,
        unmeasured,
    })
}

/// A member path as the report names it: relative to the Atlas root, with
/// forward slashes, matching [`StaleMember::member`].
fn display_member(atlas_root: &Path, path: &Path) -> String {
    path.strip_prefix(atlas_root)
        .unwrap_or(path)
        .display()
        .to_string()
        .replace('\\', "/")
}

/// Read and parse one manifest, using the member's origin content when it is
/// behind its tracked branch.
///
/// `path` lives under a registered member. When that member's origin commit is
/// present in `origin_ref_of`, the manifest text is read from that commit's
/// tree (`git show <commit>:<relative-path>`); otherwise it is read from the
/// working tree. Reading the origin tree keeps the coherence verdict measured
/// against what the stack publishes even when a checkout is behind its bump.
fn read_manifest(
    path: &Path,
    atlas_root: &Path,
    origin_ref_of: &BTreeMap<PathBuf, String>,
) -> Result<ParsedManifest, Error> {
    // Find the registered member that owns this manifest path (the longest
    // member-root prefix, so a nested crate stays under its member).
    let Some((member_path, commit)) = origin_ref_of
        .iter()
        .filter(|(member, _)| path.starts_with(member))
        .max_by_key(|(member, _)| member.components().count())
        .map(|(member, commit)| (member, commit.as_str()))
    else {
        return parse_manifest(path, atlas_root);
    };

    let relative = path
        .strip_prefix(member_path)
        .map_err(|_| Error::Manifest {
            path: path.display().to_string(),
            message: String::from("manifest is not under its member root"),
        })?;
    let relative = relative.to_string_lossy().replace('\\', "/");

    let text = git_show(member_path, commit, &relative)?;
    match text {
        Some(content) => Ok(parse_manifest_content(&content, path, atlas_root)),
        None => parse_manifest(path, atlas_root),
    }
}

/// Read one file at a revision from a member repository.
///
/// Returns `Ok(None)` when the path does not exist at that revision (a
/// manifest added since the member's origin tip), so the scan falls back to
/// the working tree rather than failing.
fn git_show(member: &Path, commit: &str, relative: &str) -> Result<Option<String>, Error> {
    let output = Command::new("git")
        .arg("--no-pager")
        .arg("-C")
        .arg(member)
        .args(["show", &format!("{commit}:{relative}")])
        .output()?;
    if output.status.success() {
        Ok(Some(String::from_utf8_lossy(&output.stdout).into_owned()))
    } else {
        Ok(None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn injected_backward_fixture_is_reported() {
        let temp =
            std::env::temp_dir().join(format!("atlas-version-coherence-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&temp);
        std::fs::create_dir_all(temp.join("repos/provider/crates/consumer"))
            .expect("fixture directory");
        std::fs::write(
            temp.join(".gitmodules"),
            "[submodule \"repos/provider\"]\npath = repos/provider\n",
        )
        .expect("gitmodules");
        std::fs::write(
            temp.join("repos/provider/Cargo.toml"),
            "[workspace]\nmembers = [\"crates/consumer\"]\n[workspace.package]\nversion = \"0.1.0\"\n[workspace.dependencies]\nprovider = { path = \".\", package = \"provider\", version = \"0.2.0\" }\n",
        )
        .expect("provider manifest");
        std::fs::write(
            temp.join("repos/provider/crates/consumer/Cargo.toml"),
            "[package]\nname = \"consumer\"\nversion = \"workspace\"\n[dependencies]\nprovider = { path = \"../..\", version = \"0.2.0\" }\n",
        )
        .expect("consumer manifest");
        // The fixture uses an explicit package version because this scanner
        // indexes package declarations, not synthetic workspace names.
        std::fs::write(
            temp.join("repos/provider/Cargo.toml"),
            "[workspace]\nmembers = [\"crates/consumer\"]\n[workspace.package]\nversion = \"0.1.0\"\n[workspace.dependencies]\nprovider = { path = \".\", package = \"provider\", version = \"0.2.0\" }\n[package]\nname = \"provider\"\nversion = \"0.1.0\"\n",
        )
        .expect("provider package manifest");
        std::fs::write(
            temp.join("repos/provider/crates/consumer/Cargo.toml"),
            "[package]\nname = \"consumer\"\nversion.workspace = true\n[dependencies]\nprovider = { workspace = true }\n",
        )
        .expect("inherited consumer manifest");
        let report = scan_atlas(&temp, View::Worktree).expect("scan fixture");
        assert_eq!(report.findings.len(), 1);
        assert_eq!(report.findings[0].actual, "0.1.0");
        let _ = std::fs::remove_dir_all(temp);
    }

    #[test]
    fn remotes_view_sees_a_provider_bump_the_pinned_trees_hide() {
        // The failure this view exists for: a provider publishes a break on its
        // default branch while every gitlink-pinned checkout still satisfies the
        // consumer's requirement, so the working-tree scan is clean. A submodule
        // cloned at a gitlink has no `origin/HEAD`, which is exactly why
        // `stale_members` cannot fall back to the remote there.
        let temp = scratch("remotes");
        let root = temp.join("atlas");

        // Provider history: 0.5.0 (the pin) then 0.6.0 (the published tip).
        let provider_upstream = temp.join("provider-upstream");
        std::fs::create_dir_all(&provider_upstream).expect("provider upstream");
        git(&provider_upstream, &["init", "-b", "main"]);
        write_package(&provider_upstream, "provider", "0.5.0");
        git(&provider_upstream, &["add", "."]);
        git(&provider_upstream, &["commit", "-m", "0.5.0"]);
        let pinned = git(&provider_upstream, &["rev-parse", "HEAD"]).expect("pinned sha");
        write_package(&provider_upstream, "provider", "0.6.0");
        git(&provider_upstream, &["add", "."]);
        git(&provider_upstream, &["commit", "-m", "0.6.0"]);

        // Consumer expects ^0.5.0 and is not swept.
        let consumer_upstream = temp.join("consumer-upstream");
        std::fs::create_dir_all(&consumer_upstream).expect("consumer upstream");
        git(&consumer_upstream, &["init", "-b", "main"]);
        std::fs::write(
            consumer_upstream.join("Cargo.toml"),
            "[package]\nname = \"consumer\"\nversion = \"0.1.0\"\n[dependencies]\nprovider = { package = \"provider\", version = \"0.5.0\", git = \"https://example/provider\" }\n",
        )
        .expect("consumer manifest");
        git(&consumer_upstream, &["add", "."]);
        git(&consumer_upstream, &["commit", "-m", "consumer"]);

        std::fs::create_dir_all(root.join("repos")).expect("repos dir");
        std::fs::write(
            root.join(".gitmodules"),
            "[submodule \"repos/provider\"]\n\tpath = repos/provider\n\turl = https://example/provider\n\n[submodule \"repos/consumer\"]\n\tpath = repos/consumer\n\turl = https://example/consumer\n",
        )
        .expect("gitmodules");

        // Both members are gitlink-shaped: fetch the tip, check out a detached
        // commit, and never create `origin/HEAD`.
        let provider = root.join("repos").join("provider");
        std::fs::create_dir_all(&provider).expect("provider dir");
        git(&provider, &["init", "-b", "main"]);
        git(
            &provider,
            &["remote", "add", "origin", &file_url(&provider_upstream)],
        );
        git(&provider, &["fetch", "--quiet", "origin", "main"]);
        git(&provider, &["checkout", "--quiet", "--detach", &pinned]);

        let consumer = root.join("repos").join("consumer");
        std::fs::create_dir_all(&consumer).expect("consumer dir");
        git(&consumer, &["init", "-b", "main"]);
        git(
            &consumer,
            &["remote", "add", "origin", &file_url(&consumer_upstream)],
        );
        git(&consumer, &["fetch", "--quiet", "origin", "main"]);
        let _ = git(
            &consumer,
            &["checkout", "--quiet", "--detach", "origin/main"],
        );

        // The recorded state is coherent: the pinned provider satisfies ^0.5.0.
        let worktree = scan_atlas(&root, View::Worktree).expect("worktree scan");
        assert_eq!(
            worktree.findings.len(),
            0,
            "the pinned trees satisfy the requirement, so the working-tree view is clean"
        );

        // The published state is not: the provider now publishes 0.6.0.
        let remotes = scan_atlas(&root, View::Remotes).expect("remotes scan");
        assert!(
            remotes.unmeasured.is_empty(),
            "both members must resolve: {:?}",
            remotes.unmeasured
        );
        assert_eq!(
            remotes.findings.len(),
            1,
            "the provider bump must be reported"
        );
        assert_eq!(remotes.findings[0].package, "provider");
        assert_eq!(remotes.findings[0].actual, "0.6.0");
        assert!(remotes.has_defect());

        let _ = std::fs::remove_dir_all(&temp);
    }

    fn write_package(repo: &Path, name: &str, version: &str) {
        std::fs::write(
            repo.join("Cargo.toml"),
            format!("[package]\nname = \"{name}\"\nversion = \"{version}\"\n"),
        )
        .expect("package manifest");
    }

    /// A local path usable as a git remote URL on Windows (forward slashes).
    fn file_url(path: &Path) -> String {
        path.to_string_lossy().replace('\\', "/")
    }

    #[test]
    fn read_manifest_prefers_origin_over_a_stale_working_tree() {
        // The gaia 0.4.0 → 0.5.0 case: the bump sits on origin while a checkout
        // is still behind. read_manifest, given the member's origin commit,
        // must parse the origin manifest (0.5.0), not the stale worktree
        // (0.4.0) — a coherence verdict against the worktree would compare
        // against a version the stack no longer publishes.
        let temp = scratch("origin-read");
        let upstream = temp.join("upstream");
        std::fs::create_dir_all(&upstream).expect("upstream dir");
        git(&upstream, &["init", "-b", "main"]);
        write_git_member(&upstream, "0.4.0");
        git(&upstream, &["add", "."]);
        git(&upstream, &["commit", "-m", "bump to 0.4.0"]);

        // Clone at 0.4.0, then advance origin to 0.5.0 so the checkout is
        // behind its own bump.
        let member = temp.join("repos").join("member");
        std::fs::create_dir_all(temp.join("repos")).expect("repos dir");
        clone(&upstream, &member);
        write_git_member(&upstream, "0.5.0");
        git(&upstream, &["add", "."]);
        git(&upstream, &["commit", "-m", "bump to 0.5.0"]);
        git(&member, &["fetch", "--quiet", "origin"]);
        let origin_commit = git(&member, &["rev-parse", "origin/main"]).expect("origin tip");

        let manifest_path = member.join("Cargo.toml");
        let mut origin_map = BTreeMap::new();
        origin_map.insert(member.clone(), origin_commit);

        let parsed = read_manifest(&manifest_path, &temp, &origin_map).expect("read manifest");
        // origin publishes 0.5.0, so the parsed package version is 0.5.0 — not
        // the stale 0.4.0 the working tree carries.
        assert_eq!(parsed.package_version.as_deref(), Some("0.5.0"));

        // Without the origin map the same manifest reads the stale worktree.
        let parsed = read_manifest(&manifest_path, &temp, &BTreeMap::new()).expect("read manifest");
        assert_eq!(parsed.package_version.as_deref(), Some("0.4.0"));

        let _ = std::fs::remove_dir_all(&temp);
    }

    fn git(repo: &Path, args: &[&str]) -> Option<String> {
        Command::new("git")
            .arg("-C")
            .arg(repo)
            .arg("-c")
            .arg("user.email=guard@atlas.test")
            .arg("-c")
            .arg("user.name=Guard Test")
            .args(args)
            .output()
            .ok()
            .filter(|out| out.status.success())
            .map(|out| String::from_utf8_lossy(&out.stdout).trim().to_owned())
    }

    fn clone(from: &Path, to: &Path) {
        assert!(
            Command::new("git")
                .args(["clone", "--quiet"])
                .arg(from)
                .arg(to)
                .output()
                .is_ok_and(|out| out.status.success()),
            "git clone {from:?} -> {to:?} failed"
        );
    }

    fn scratch(name: &str) -> PathBuf {
        let root = std::env::temp_dir().join(format!(
            "atlas-version-coherence-{name}-{}-{:?}",
            std::process::id(),
            std::thread::current().id()
        ));
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(&root).expect("scratch root");
        root
    }

    fn write_git_member(repo: &Path, version: &str) {
        std::fs::write(
            repo.join("Cargo.toml"),
            format!(
                "[workspace]\nmembers = [\".\"]\n[workspace.package]\nversion = \"{version}\"\n[package]\nname = \"member\"\nversion = \"{version}\"\n"
            ),
        )
        .expect("member manifest");
    }
}

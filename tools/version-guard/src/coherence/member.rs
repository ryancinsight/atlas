use std::fs;
use std::path::{Component, Path, PathBuf};
use std::process::Command;

use serde::Serialize;

use crate::error::Error;

use super::manifest::{DependencySpec, ParsedManifest};

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Member {
    pub(crate) path: PathBuf,
    url: String,
}

pub(crate) fn registered_members(atlas_root: &Path) -> Result<Vec<Member>, Error> {
    let modules = atlas_root.join(".gitmodules");
    let text = fs::read_to_string(&modules).map_err(|source| Error::Manifest {
        path: modules.display().to_string(),
        message: source.to_string(),
    })?;
    let mut members = Vec::new();
    let mut path: Option<PathBuf> = None;
    let mut url: Option<String> = None;
    for line in text.lines().chain(std::iter::once("")) {
        if let Some((key, value)) = line.split_once('=') {
            match key.trim() {
                "path" => path = Some(atlas_root.join(value.trim())),
                "url" => url = Some(value.trim().trim_end_matches(".git").to_string()),
                _ => {}
            }
            continue;
        }
        if let Some(path) = path.take() {
            if !path.is_dir() {
                // Registered in `.gitmodules` but not materialized: a
                // promotion mid-flight (the entry landed before the
                // submodule was added), so a clean checkout has no
                // directory here at all. There are no manifests to
                // check, so skipping is sound — and failing closed
                // would hold the fleet gate hostage to one
                // registration. The promotion item owns the follow-up.
                eprintln!(
                    "warning: registered member directory is missing, skipping: {}",
                    path.display()
                );
                // Drop the pending url with the skipped entry: otherwise the
                // next section inherits it if it declares no url of its own.
                url.take();
                continue;
            }
            members.push(Member {
                path,
                url: url.take().unwrap_or_default(),
            });
        }
    }
    members.sort_by(|a, b| a.path.cmp(&b.path));
    members.dedup_by(|a, b| a.path == b.path);
    Ok(members)
}

pub(crate) fn is_first_party_source(
    manifest: &ParsedManifest,
    dependency: &DependencySpec,
    members: &[Member],
    _atlas_root: &Path,
) -> bool {
    if let Some(path) = dependency.path.as_deref() {
        let base = if dependency.workspace {
            members
                .iter()
                .find(|member| manifest.path.starts_with(&member.path))
                .map_or_else(
                    || manifest.path.parent(),
                    |member| Some(member.path.as_path()),
                )
        } else {
            manifest.path.parent()
        };
        let Some(base) = base else {
            return false;
        };
        let Ok(resolved) = fs::canonicalize(base.join(path)) else {
            return false;
        };
        return members.iter().any(|member| {
            fs::canonicalize(&member.path).is_ok_and(|member_path| {
                resolved == member_path || resolved.starts_with(&member_path)
            })
        });
    }
    if let Some(git) = dependency.git.as_deref() {
        return git_url_names_member(git, members);
    }
    false
}

/// Whether a `git =` URL names one of the registered members.
///
/// The comparison is by URL, so it needs no filesystem: a manifest read from a
/// git tree classifies the same as one read from a working tree.
fn git_url_names_member(git: &str, members: &[Member]) -> bool {
    let normalized = git.trim_end_matches(".git").to_ascii_lowercase();
    members
        .iter()
        .any(|member| !member.url.is_empty() && member.url.to_ascii_lowercase() == normalized)
}

/// Fold `.` and `..` out of a path without touching the filesystem.
///
/// `Path::canonicalize` is the wrong tool for a manifest read from a git tree:
/// a crate added since the checkout has no on-disk directory to canonicalize,
/// and a `..` that escapes the tree must not silently resolve to an unrelated
/// directory that happens to exist.
fn normalize_lexically(path: &Path) -> PathBuf {
    let mut folded: Vec<Component> = Vec::new();
    for component in path.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir => {
                if matches!(folded.last(), Some(Component::Normal(_))) {
                    folded.pop();
                } else {
                    // A `..` above a root or prefix has nowhere to go; keep it
                    // so the result cannot be mistaken for a location inside
                    // the tree.
                    folded.push(component);
                }
            }
            other => folded.push(other),
        }
    }
    folded.iter().collect()
}

/// True when `candidate` resolves under `base` after lexical folding.
pub(crate) fn lexically_under(base: &Path, candidate: &Path) -> bool {
    normalize_lexically(candidate).starts_with(normalize_lexically(base))
}

/// First-party detection that does not require the dependency to exist on disk.
///
/// This is the tree-view counterpart to [`is_first_party_source`]. A path
/// dependency is judged by lexical containment in a member root rather than by
/// `canonicalize`, so a manifest read at a remote tip classifies correctly even
/// when the crate it names is newer than the local checkout.
pub(crate) fn is_first_party_source_in_tree(
    manifest: &ParsedManifest,
    dependency: &DependencySpec,
    members: &[Member],
) -> bool {
    if let Some(path) = dependency.path.as_deref() {
        let base = if dependency.workspace {
            members
                .iter()
                .find(|member| manifest.path.starts_with(&member.path))
                .map_or_else(
                    || manifest.path.parent(),
                    |member| Some(member.path.as_path()),
                )
        } else {
            manifest.path.parent()
        };
        let Some(base) = base else {
            return false;
        };
        let resolved = base.join(path);
        return members
            .iter()
            .any(|member| lexically_under(&member.path, &resolved));
    }
    if let Some(git) = dependency.git.as_deref() {
        return git_url_names_member(git, members);
    }
    false
}

/// List a member's `Cargo.toml` paths as recorded at `commit`.
///
/// The returned paths are rooted at the member's own directory so the caller
/// can reuse the same manifest reader and report path as the working-tree scan.
/// Build and run-output trees are excluded by the same predicate the working
/// tree walk uses, so a `target/`-resident manifest cannot be read from a tree
/// either.
///
/// # Errors
///
/// Returns [`Error::Git`] when `git ls-tree` cannot be executed or fails.
pub(crate) fn remote_manifest_paths(member: &Member, commit: &str) -> Result<Vec<PathBuf>, Error> {
    let output = Command::new("git")
        .arg("--no-pager")
        .arg("-C")
        .arg(&member.path)
        .args(["ls-tree", "-r", "--name-only", commit])
        .output()?;
    if !output.status.success() {
        return Err(Error::Git {
            command: format!(
                "git -C {} ls-tree -r --name-only {commit}",
                member.path.display()
            ),
            stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
        });
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut paths = Vec::new();
    for line in stdout.lines() {
        let relative = Path::new(line.trim());
        if relative.file_name().and_then(|name| name.to_str()) != Some("Cargo.toml") {
            continue;
        }
        let skipped = relative.components().any(|component| match component {
            Component::Normal(name) => name.to_str().is_some_and(is_not_source_tree),
            _ => false,
        });
        if skipped {
            continue;
        }
        paths.push(member.path.join(relative));
    }
    paths.sort();
    Ok(paths)
}

/// A directory the manifest walk could not read.
///
/// Build and run-output trees carry directories the scanning user cannot
/// traverse -- a `pytest` cache under a member's output root is the observed
/// case on Windows. Such a directory holds no package manifest, so the walk
/// steps over it; recording it is what keeps the step from also concealing an
/// unreadable *source* directory, whose manifests would then go unmeasured
/// while the report still read clean.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct UnreadableDir {
    /// The directory that could not be read.
    pub path: PathBuf,
    /// The operating system's reason.
    pub reason: String,
}

/// True for a directory that cannot contain a package manifest: a build or
/// run-output tree, or any dotted directory (`.git`, `.venv`, tool caches).
fn is_not_source_tree(name: &str) -> bool {
    name.starts_with('.') || matches!(name, "target" | "output" | "outputs" | "test_output")
}

pub(crate) fn collect_manifests(
    root: &Path,
    output: &mut Vec<PathBuf>,
    unreadable: &mut Vec<UnreadableDir>,
) -> Result<(), Error> {
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let entries = match fs::read_dir(&dir) {
            Ok(entries) => entries,
            Err(source) => {
                unreadable.push(UnreadableDir {
                    path: dir,
                    reason: source.to_string(),
                });
                continue;
            }
        };
        for entry in entries {
            let entry = entry.map_err(|source| Error::Manifest {
                path: dir.display().to_string(),
                message: source.to_string(),
            })?;
            let path = entry.path();
            let name = entry.file_name();
            let name = name.to_string_lossy();
            if path.is_dir() {
                if is_not_source_tree(name.as_ref()) {
                    continue;
                }
                stack.push(path);
            } else if name == "Cargo.toml" {
                output.push(path);
            }
        }
    }
    output.sort();
    Ok(())
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;
    use std::fs;

    #[test]
    fn missing_member_directory_skips_instead_of_aborting() {
        let root =
            std::env::temp_dir().join(format!("version-guard-member-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join("repos/present")).unwrap();
        fs::create_dir_all(root.join("repos/bare")).unwrap();
        fs::write(
            root.join(".gitmodules"),
            "[submodule \"repos/missing\"]\n\tpath = repos/missing\n\turl = https://example/missing\n\n[submodule \"repos/present\"]\n\tpath = repos/present\n\turl = https://example/present\n\n[submodule \"repos/bare\"]\n\tpath = repos/bare\n",
        )
        .unwrap();

        let members = registered_members(&root).expect("missing dir must skip, not abort");
        assert_eq!(members.len(), 2);
        let by_path = |name: &str| {
            members
                .iter()
                .find(|member| member.path == root.join("repos").join(name))
                .unwrap_or_else(|| panic!("expected member {name}"))
        };
        // `present` keeps its own url …
        assert_eq!(by_path("present").url, "https://example/present");
        // … and the skipped entry's url must not leak into the url-less one.
        assert!(by_path("bare").url.is_empty());
        let _ = fs::remove_dir_all(root);
    }
}

#[cfg(test)]
mod tree_tests {
    #![allow(clippy::unwrap_used)]

    use super::*;
    use std::fs;
    use std::process::Command;

    fn git(repo: &Path, args: &[&str]) {
        let ran = Command::new("git")
            .arg("-C")
            .arg(repo)
            .args(["-c", "user.email=t@atlas.test"])
            .args(["-c", "user.name=T"])
            .args(args)
            .status()
            .unwrap()
            .success();
        assert!(ran, "git {args:?} failed in {repo:?}");
    }

    fn git_stdout(repo: &Path, args: &[&str]) -> String {
        let output = Command::new("git")
            .arg("-C")
            .arg(repo)
            .args(args)
            .output()
            .unwrap();
        assert!(output.status.success(), "git {args:?} failed");
        String::from_utf8_lossy(&output.stdout).trim().to_owned()
    }

    #[test]
    fn lexical_folding_accepts_descent_and_rejects_escapes() {
        assert!(lexically_under(Path::new("/a/b"), Path::new("/a/b")));
        assert!(lexically_under(Path::new("/a/b"), Path::new("/a/b/c/../d")));
        // A `..` that leaves the base must not fold into a false match, and a
        // sibling sharing a textual prefix must not either.
        assert!(!lexically_under(Path::new("/a/b"), Path::new("/a/b/../c")));
        assert!(!lexically_under(Path::new("/a/b"), Path::new("/a/bb")));
    }

    #[test]
    fn remote_manifest_paths_takes_cargo_manifests_and_skips_output_trees() {
        let root = std::env::temp_dir().join(format!("version-guard-tree-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join("crates/x")).unwrap();
        fs::create_dir_all(root.join("target")).unwrap();
        fs::create_dir_all(root.join("output")).unwrap();
        fs::write(root.join("Cargo.toml"), "[workspace]\n").unwrap();
        fs::write(
            root.join("crates/x/Cargo.toml"),
            "[package]\nname = \"x\"\n",
        )
        .unwrap();
        // A manifest under an output tree is committed state but not measured
        // state: the working-tree walk skips these trees, so a tree read must
        // agree, or the two views would not be comparable.
        fs::write(root.join("target/Cargo.toml"), "[package]\nname = \"t\"\n").unwrap();
        fs::write(root.join("output/Cargo.toml"), "[package]\nname = \"o\"\n").unwrap();
        fs::write(root.join("README.md"), "x\n").unwrap();
        git(&root, &["init", "-b", "main"]);
        git(&root, &["add", "."]);
        git(&root, &["commit", "-m", "fixture"]);
        let commit = git_stdout(&root, &["rev-parse", "HEAD"]);

        let member = Member {
            path: root.clone(),
            url: String::new(),
        };
        let paths = remote_manifest_paths(&member, &commit).unwrap();
        assert_eq!(
            paths,
            vec![root.join("Cargo.toml"), root.join("crates/x/Cargo.toml")]
        );
        let _ = fs::remove_dir_all(&root);
    }
}

#[cfg(test)]
mod walk_tests {
    #![allow(clippy::unwrap_used)]

    use super::*;
    use std::fs;

    fn scratch(tag: &str) -> PathBuf {
        let root =
            std::env::temp_dir().join(format!("version-guard-walk-{tag}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(&root).unwrap();
        root
    }

    #[test]
    fn output_and_dotted_trees_carry_no_measured_manifest() {
        let root = scratch("skip");
        for buried in [
            "target",
            "output",
            "outputs",
            "test_output",
            ".pytest_cache",
        ] {
            let dir = root.join(buried).join("nested");
            fs::create_dir_all(&dir).unwrap();
            fs::write(dir.join("Cargo.toml"), "[package]\nname = \"buried\"\n").unwrap();
        }
        let source = root.join("crates").join("real");
        fs::create_dir_all(&source).unwrap();
        fs::write(source.join("Cargo.toml"), "[package]\nname = \"real\"\n").unwrap();

        let mut manifests = Vec::new();
        let mut unreadable = Vec::new();
        collect_manifests(&root, &mut manifests, &mut unreadable).unwrap();

        assert_eq!(manifests, vec![source.join("Cargo.toml")]);
        assert!(
            unreadable.is_empty(),
            "readable tree reported as unreadable"
        );
        let _ = fs::remove_dir_all(&root);
    }

    #[test]
    fn unreadable_directory_is_recorded_rather_than_aborting_the_scan() {
        // A directory the walk cannot read surfaces as a `read_dir` error --
        // the ACL-denied `pytest` cache under a member's output root is the
        // observed case. An absent root produces the same error deterministically
        // and on every platform, which is what this pins: the error is recorded
        // and the walk returns, rather than aborting the fleet scan.
        let root = scratch("unreadable");
        let absent = root.join("absent");

        let mut manifests = Vec::new();
        let mut unreadable = Vec::new();
        collect_manifests(&absent, &mut manifests, &mut unreadable).unwrap();

        assert!(manifests.is_empty());
        assert_eq!(
            unreadable
                .iter()
                .map(|entry| entry.path.clone())
                .collect::<Vec<_>>(),
            vec![absent],
            "an unreadable directory must be recorded, not silently skipped"
        );
        assert!(
            !unreadable[0].reason.is_empty(),
            "the reason must reach the reader"
        );
        let _ = fs::remove_dir_all(&root);
    }
}

use std::fs;
use std::path::{Path, PathBuf};

use crate::error::Error;

use super::manifest::{DependencySpec, ParsedManifest};

#[derive(Debug, Clone)]
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
        let normalized = git.trim_end_matches(".git").to_ascii_lowercase();
        return members
            .iter()
            .any(|member| !member.url.is_empty() && member.url.to_ascii_lowercase() == normalized);
    }
    false
}

pub(crate) fn collect_manifests(root: &Path, output: &mut Vec<PathBuf>) -> Result<(), Error> {
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let entries = fs::read_dir(&dir).map_err(|source| Error::Manifest {
            path: dir.display().to_string(),
            message: source.to_string(),
        })?;
        for entry in entries {
            let entry = entry.map_err(|source| Error::Manifest {
                path: dir.display().to_string(),
                message: source.to_string(),
            })?;
            let path = entry.path();
            let name = entry.file_name();
            let name = name.to_string_lossy();
            if path.is_dir() {
                if matches!(name.as_ref(), ".git" | "target" | "output" | "outputs") {
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

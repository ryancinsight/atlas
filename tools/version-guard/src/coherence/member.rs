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
                return Err(Error::Manifest {
                    path: path.display().to_string(),
                    message: String::from("registered member directory is missing"),
                });
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

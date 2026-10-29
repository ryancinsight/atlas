//! Resolve a dependency to its registered provider before looking up a package.

use std::fs;
use std::path::{Path, PathBuf};

use crate::error::Error;

use super::View;
use super::manifest::{DependencySpec, ParsedManifest};
use super::member::{Member, normalize_lexically};

/// Versions are values of this identity plus a package name, never part of the
/// key: two versions of the same provider's package must still conflict.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub(super) enum ProviderId {
    Git(String),
    Local(PathBuf),
}

fn git_identity(url: &str) -> String {
    url.to_ascii_lowercase()
        .trim_end_matches(".git")
        .to_string()
}

fn provider_id(member: &Member) -> ProviderId {
    if member.url.is_empty() {
        ProviderId::Local(normalize_lexically(&member.path))
    } else {
        ProviderId::Git(git_identity(&member.url))
    }
}

/// Find the most specific registered root. Equal-depth aliases must agree on
/// the provider; choosing the first one would make comparisons order-dependent.
pub(super) fn path_provider(
    path: &Path,
    members: &[Member],
    view: View,
) -> Result<Option<ProviderId>, Error> {
    let resolve = |path: &Path| match view {
        View::Worktree => fs::canonicalize(path).ok(),
        View::Remotes => Some(normalize_lexically(path)),
    };
    let Some(resolved) = resolve(path) else {
        return Ok(None);
    };
    let mut selected: Option<(usize, ProviderId, bool)> = None;
    for member in members {
        let Some(root) = resolve(&member.path) else {
            continue;
        };
        if !resolved.starts_with(&root) {
            continue;
        }
        let depth = root.components().count();
        let provider = provider_id(member);
        match &selected {
            Some((previous, _, _)) if *previous > depth => {}
            Some((previous, identity, ambiguous)) if *previous == depth => {
                selected = Some((depth, provider.clone(), *ambiguous || *identity != provider));
            }
            _ => selected = Some((depth, provider, false)),
        }
    }
    if selected
        .as_ref()
        .is_some_and(|(_, _, ambiguous)| *ambiguous)
    {
        return Err(Error::Manifest {
            path: path.display().to_string(),
            message: String::from("path names multiple registered providers"),
        });
    }
    Ok(selected.map(|(_, provider, _)| provider))
}

pub(super) fn dependency_provider(
    manifest: &ParsedManifest,
    dependency: &DependencySpec,
    members: &[Member],
    view: View,
) -> Result<Option<ProviderId>, Error> {
    if let Some(path) = dependency.path.as_deref() {
        let base = dependency
            .declared_at
            .as_deref()
            .and_then(Path::parent)
            .or_else(|| manifest.path.parent());
        return match base {
            Some(base) => path_provider(&base.join(path), members, view),
            None => Ok(None),
        };
    }
    Ok(dependency.git.as_deref().and_then(|git| {
        let normalized = git_identity(git);
        members
            .iter()
            .any(|member| !member.url.is_empty() && git_identity(&member.url) == normalized)
            .then_some(ProviderId::Git(normalized))
    }))
}

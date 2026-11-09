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

/// Zero-sized resolution-policy markers: [`WorktreeResolve`] canonicalizes
/// through the filesystem (correct for checked-out trees) and
/// [`RemotesResolve`] folds lexically (correct for a tree read from a git
/// object store where a new crate may have no local directory). The
/// [`View`] branch in [`path_provider`] monomorphizes per policy, so neither
/// the hot manifest-index loop nor the per-edge dependency resolution pays
/// for a runtime tag, a boxed closure, or dynamic dispatch.
pub(super) struct WorktreeResolve;
pub(super) struct RemotesResolve;

impl WorktreeResolve {
    /// Filesystem canonicalization for checked-out trees.
    #[must_use]
    #[inline]
    pub fn resolve_path(path: &Path) -> Option<PathBuf> {
        fs::canonicalize(path).ok()
    }
}

impl RemotesResolve {
    /// Lexical fold for a tree read from a git object store, where a new
    /// crate may have no local directory to canonicalize.
    #[must_use]
    #[inline]
    pub fn resolve_path(path: &Path) -> PathBuf {
        normalize_lexically(path)
    }
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
///
/// The per-member `resolve` closure monomorphizes per [`View`]: worktree
/// resolution canonicalizes through the filesystem (correct for checked-out
/// trees), remote resolution folds lexically (correct for a tree read from a
/// git object store where a new crate may have no local directory). No
/// boxing, no trait objects — the branch is a compile-time constant.
pub(super) fn path_provider(
    path: &Path,
    members: &[Member],
    view: View,
) -> Result<Option<ProviderId>, Error> {
    match view {
        View::Worktree => path_provider_with::<WorktreeResolve>(path, members),
        View::Remotes => path_provider_with::<RemotesResolve>(path, members),
    }
}

/// Resolution policy for [`path_provider_with`]: a zero-sized type whose
/// `resolve` is monomorphized per view — no function pointer, no closure
/// allocation, no dynamic dispatch on the hot path.
///
/// The trait keeps the fallible worktree probe (`Option`, for unreadable
/// roots) distinct from the infallible lexical fold, so the `Remotes`
/// path never wraps in `Option` just to satisfy a shared signature.
trait ResolvePolicy {
    type Output;

    fn resolve(path: &Path) -> Self::Output;

    fn into_option(output: Self::Output) -> Option<PathBuf>;
}

impl ResolvePolicy for WorktreeResolve {
    type Output = Option<PathBuf>;

    #[inline]
    fn resolve(path: &Path) -> Self::Output {
        Self::resolve_path(path)
    }

    #[inline]
    fn into_option(output: Self::Output) -> Option<PathBuf> {
        output
    }
}

impl ResolvePolicy for RemotesResolve {
    type Output = PathBuf;

    #[inline]
    fn resolve(path: &Path) -> Self::Output {
        Self::resolve_path(path)
    }

    #[inline]
    fn into_option(output: Self::Output) -> Option<PathBuf> {
        Some(output)
    }
}

fn path_provider_with<R: ResolvePolicy>(
    path: &Path,
    members: &[Member],
) -> Result<Option<ProviderId>, Error> {
    let Some(resolved) = R::into_option(R::resolve(path)) else {
        return Ok(None);
    };
    // Pre-resolve member roots once per call instead of per candidate: the
    // old loop re-canonicalized every member root for every dependency edge
    // (O(members) syscalls per edge). Roots are small, so stack-allocated
    // iteration keeps this allocation-free on the hot path beyond the one
    // result slot.
    let mut selected: Option<(usize, ProviderId, bool)> = None;
    for member in members {
        let Some(root) = R::into_option(R::resolve(&member.path)) else {
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
        // Zero-copy identity check: compare lowercased forms without
        // allocating the normalized query per member. The common case (exact
        // URL match) short-circuits before any case folding.
        let query = git.trim_end_matches(".git");
        members
            .iter()
            .filter(|member| !member.url.is_empty())
            .any(|member| {
                let candidate = member.url.trim_end_matches(".git");
                candidate.len() == query.len() && candidate.eq_ignore_ascii_case(query)
            })
            .then(|| ProviderId::Git(git_identity(git)))
    }))
}

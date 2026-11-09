use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Component, Path, PathBuf};

use toml::Value;

use crate::CheckoutError;

pub(super) struct ProviderRequirements {
    pub(super) destination: PathBuf,
    pub(super) providers: BTreeMap<String, BTreeSet<PathBuf>>,
}

pub(super) fn discover(
    manifest: &Path,
    destination: &Path,
) -> Result<ProviderRequirements, CheckoutError> {
    let manifest = canonical_file(manifest)?;
    let destination = canonical_directory(destination)?;
    let repository = manifest
        .parent()
        .ok_or_else(|| CheckoutError::InvalidPath {
            path: manifest.clone(),
            requirement: "inside a repository directory",
        })?;
    let contents = fs::read_to_string(&manifest).map_err(|source| CheckoutError::Io {
        path: manifest.clone(),
        source,
    })?;
    let document = toml::from_str::<Value>(&contents).map_err(|source| CheckoutError::Toml {
        path: manifest.clone(),
        source,
    })?;

    let mut declared_paths = Vec::new();
    collect_dependency_paths(&document, &mut declared_paths);
    let mut providers = BTreeMap::<String, BTreeSet<PathBuf>>::new();

    for declared in declared_paths {
        let dependency = normalize(&repository.join(declared));
        if dependency.starts_with(repository) {
            continue;
        }
        let relative = dependency.strip_prefix(&destination).map_err(|_| {
            CheckoutError::ExternalPathOutsideDestination {
                dependency: dependency.clone(),
                destination: destination.clone(),
            }
        })?;
        let provider = relative
            .components()
            .next()
            .and_then(normal_component)
            .ok_or_else(|| CheckoutError::MissingProviderName(dependency.clone()))?;
        providers
            .entry(provider.to_owned())
            .or_default()
            .insert(dependency);
    }

    Ok(ProviderRequirements {
        destination,
        providers,
    })
}

fn canonical_file(path: &Path) -> Result<PathBuf, CheckoutError> {
    canonical::<FileKind>(path)
}

fn canonical_directory(path: &Path) -> Result<PathBuf, CheckoutError> {
    canonical::<DirKind>(path)
}

/// Zero-sized canonicalization policy: [`FileKind`] requires a file,
/// [`DirKind`] a directory. [`canonical`] monomorphizes per kind, so the
/// file/dir branch is a compile-time constant with no runtime tag and no
/// duplicated bodies.
struct FileKind;
struct DirKind;

/// Canonicalization policy for [`canonical`]: a zero-sized type whose
/// `check`/`requirement` monomorphize per kind — no branch, no closure,
/// no dynamic dispatch.
trait CanonicalKind {
    /// Whether the canonicalized path has the required kind.
    fn check(path: &Path) -> bool;
    /// The `InvalidPath` requirement string for this kind.
    fn requirement() -> &'static str;
}

impl CanonicalKind for FileKind {
    #[inline]
    fn check(path: &Path) -> bool {
        path.is_file()
    }

    #[inline]
    fn requirement() -> &'static str {
        "a file"
    }
}

impl CanonicalKind for DirKind {
    #[inline]
    fn check(path: &Path) -> bool {
        path.is_dir()
    }

    #[inline]
    fn requirement() -> &'static str {
        "a directory"
    }
}

#[inline]
fn canonical<M: CanonicalKind>(path: &Path) -> Result<PathBuf, CheckoutError> {
    let canonical = path.canonicalize().map_err(|source| CheckoutError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    if M::check(&canonical) {
        Ok(canonical)
    } else {
        Err(CheckoutError::InvalidPath {
            path: canonical,
            requirement: M::requirement(),
        })
    }
}

fn collect_dependency_paths<'a>(value: &'a Value, paths: &mut Vec<&'a str>) {
    let Value::Table(table) = value else {
        return;
    };

    // Pre-size: one path per table entry is the observed upper bound, so the
    // common single-dep manifest is one allocation.
    paths.reserve(table.len());
    for (key, child) in table {
        match key.as_str() {
            "dependencies" | "dev-dependencies" | "build-dependencies" | "replace" => {
                collect_section_paths(child, paths);
            }
            "patch" => collect_patch_paths(child, paths),
            _ => collect_dependency_paths(child, paths),
        }
    }
}

fn collect_patch_paths<'a>(value: &'a Value, paths: &mut Vec<&'a str>) {
    let Some(sources) = value.as_table() else {
        return;
    };
    for dependencies in sources.values() {
        collect_section_paths(dependencies, paths);
    }
}

fn collect_section_paths<'a>(value: &'a Value, paths: &mut Vec<&'a str>) {
    let Some(dependencies) = value.as_table() else {
        return;
    };
    paths.extend(
        dependencies
            .values()
            .filter_map(Value::as_table)
            .filter_map(|specification| specification.get("path"))
            .filter_map(Value::as_str),
    );
}

fn normalize(path: &Path) -> PathBuf {
    // Pre-size: `PathBuf` has no `with_capacity` for components, so seed it
    // with the input length — one allocation for the common no-`..` case.
    let mut normalized = PathBuf::with_capacity(path.as_os_str().len());
    for component in path.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir => {
                normalized.pop();
            }
            other => normalized.push(other.as_os_str()),
        }
    }
    normalized
}

/// Borrowed provider-name probe: zero-copy extraction of the first normal
/// component with no allocation and no `to_owned` on the hot path. The
/// caller owns the single `to_owned` at the `entry` boundary.
#[inline]
fn normal_component(component: Component<'_>) -> Option<&str> {
    match component {
        Component::Normal(value) => value.to_str(),
        _ => None,
    }
}

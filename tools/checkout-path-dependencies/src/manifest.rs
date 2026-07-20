use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Component, Path, PathBuf};

use toml::Value;

use crate::CheckoutError;

pub(super) struct ProviderRequirements {
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

    Ok(ProviderRequirements { providers })
}

fn canonical_file(path: &Path) -> Result<PathBuf, CheckoutError> {
    let canonical = path.canonicalize().map_err(|source| CheckoutError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    if canonical.is_file() {
        Ok(canonical)
    } else {
        Err(CheckoutError::InvalidPath {
            path: canonical,
            requirement: "a file",
        })
    }
}

fn canonical_directory(path: &Path) -> Result<PathBuf, CheckoutError> {
    let canonical = path.canonicalize().map_err(|source| CheckoutError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    if canonical.is_dir() {
        Ok(canonical)
    } else {
        Err(CheckoutError::InvalidPath {
            path: canonical,
            requirement: "a directory",
        })
    }
}

fn collect_dependency_paths<'a>(value: &'a Value, paths: &mut Vec<&'a str>) {
    let Value::Table(table) = value else {
        return;
    };

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
    let mut normalized = PathBuf::new();
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

fn normal_component(component: Component<'_>) -> Option<&str> {
    match component {
        Component::Normal(value) => value.to_str(),
        _ => None,
    }
}

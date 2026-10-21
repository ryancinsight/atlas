use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use crate::error::Error;

use super::View;
use super::member::Member;
use super::source::{ProviderId, path_provider};
use super::toml::{dependency_specs_from_sections, section_flag, section_value, sections};

#[derive(Debug, Clone)]
pub(crate) struct ParsedManifest {
    pub(crate) consumer: String,
    pub(crate) display_path: String,
    pub(crate) path: PathBuf,
    pub(crate) is_root: bool,
    pub(crate) package_name: Option<String>,
    pub(crate) package_version: Option<String>,
    pub(crate) workspace_version: Option<String>,
    pub(crate) package_version_workspace: bool,
    pub(crate) dependencies: Vec<DependencySpec>,
    pub(crate) workspace_dependencies: Vec<DependencySpec>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct DependencySpec {
    pub(crate) key: String,
    pub(crate) package: Option<String>,
    pub(crate) version: Option<String>,
    pub(crate) path: Option<String>,
    pub(crate) git: Option<String>,
    pub(crate) workspace: bool,
    pub(crate) first_party_source: bool,
    /// Retained when a workspace dependency is inherited by a nested crate.
    pub(crate) declared_at: Option<PathBuf>,
}

#[derive(Debug, Clone)]
pub(crate) struct PackageVersion {
    pub(crate) version: String,
}

pub(crate) fn parse_manifest(path: &Path, atlas_root: &Path) -> Result<ParsedManifest, Error> {
    let text = fs::read_to_string(path).map_err(|source| Error::Manifest {
        path: path.display().to_string(),
        message: source.to_string(),
    })?;
    Ok(parse_manifest_content(&text, path, atlas_root))
}

/// Parse a manifest from in-memory content.
///
/// Used by the coherence scan to read a behind member's manifests at the ref
/// the stack publishes (its origin) rather than at the possibly-stale working
/// tree. `path` is still the on-disk manifest path — it derives the consumer
/// and report path — but the parsed content comes from the caller.
pub(crate) fn parse_manifest_content(text: &str, path: &Path, atlas_root: &Path) -> ParsedManifest {
    let section = sections(text);
    let package_name = section_value(&section, "package", "name");
    let package_version_raw = section_value(&section, "package", "version");
    let package_version_workspace = section_flag(&section, "package", "version.workspace")
        || package_version_raw.as_deref() == Some("workspace = true");
    let package_version = package_version_raw.filter(|value| value != "workspace = true");
    let workspace_version = section_value(&section, "workspace.package", "version");
    let mut dependencies = dependency_specs_from_sections(&section, false);
    let mut workspace_dependencies = dependency_specs_from_sections(&section, true);
    for dependency in dependencies.iter_mut().chain(&mut workspace_dependencies) {
        dependency.declared_at = Some(path.to_path_buf());
    }
    let consumer = path
        .strip_prefix(atlas_root)
        .ok()
        .and_then(|p| p.components().nth(1))
        .map_or_else(
            || String::from("unknown"),
            |c| c.as_os_str().to_string_lossy().into_owned(),
        );
    // TOML creates the parent workspace table implicitly for any child table.
    let is_root = section
        .keys()
        .any(|name| name == "workspace" || name.starts_with("workspace."));
    ParsedManifest {
        consumer,
        display_path: path
            .strip_prefix(atlas_root)
            .unwrap_or(path)
            .display()
            .to_string(),
        path: path.to_path_buf(),
        is_root,
        package_name,
        package_version,
        workspace_version,
        package_version_workspace,
        dependencies,
        workspace_dependencies,
    }
}

pub(crate) fn package_index(
    manifests: &[ParsedManifest],
    members: &[Member],
) -> Result<BTreeMap<(ProviderId, String), PackageVersion>, Error> {
    let roots: BTreeMap<_, _> = manifests
        .iter()
        .filter(|manifest| manifest.is_root)
        .filter_map(|manifest| {
            Some((
                manifest.path.parent()?.to_path_buf(),
                manifest.workspace_version.clone(),
            ))
        })
        .collect();
    let mut index: BTreeMap<(ProviderId, String), PackageVersion> = BTreeMap::new();
    for manifest in manifests {
        let Some(name) = manifest.package_name.as_deref() else {
            continue;
        };
        let version = manifest.package_version.clone().or_else(|| {
            if manifest.package_version_workspace {
                workspace_root(manifest, &roots).cloned().flatten()
            } else {
                None
            }
        });
        if let Some(version) = version {
            // Manifest paths identify their registered tree even when their
            // contents came from an origin commit newer than the checkout.
            let provider =
                path_provider(&manifest.path, members, View::Remotes)?.ok_or_else(|| {
                    Error::Manifest {
                        path: manifest.display_path.clone(),
                        message: String::from("package is outside registered providers"),
                    }
                })?;
            let key = (provider, name.to_string());
            if let Some(existing) = index.get(&key) {
                if existing.version != version {
                    return Err(Error::Manifest {
                        path: manifest.display_path.clone(),
                        message: format!(
                            "ambiguous first-party package `{name}` has versions {} and {version}",
                            existing.version
                        ),
                    });
                }
            } else {
                index.insert(key, PackageVersion { version });
            }
        }
    }
    Ok(index)
}

pub(crate) fn workspace_dependency_index(
    manifests: &[ParsedManifest],
) -> BTreeMap<PathBuf, BTreeMap<String, DependencySpec>> {
    let mut result = BTreeMap::new();
    for manifest in manifests {
        if manifest.is_root
            && let Some(directory) = manifest.path.parent()
        {
            result.insert(
                directory.to_path_buf(),
                manifest
                    .workspace_dependencies
                    .iter()
                    .map(|dep| (dep.key.clone(), dep.clone()))
                    .collect(),
            );
        }
    }
    result
}

pub(crate) fn dependency_specs(
    manifest: &ParsedManifest,
    workspace_deps: &BTreeMap<PathBuf, BTreeMap<String, DependencySpec>>,
) -> Vec<DependencySpec> {
    manifest
        .dependencies
        .iter()
        .map(|dependency| {
            if dependency.workspace {
                workspace_root(manifest, workspace_deps)
                    .and_then(|dependencies| dependencies.get(&dependency.key))
                    .cloned()
                    .unwrap_or_else(|| dependency.clone())
            } else {
                dependency.clone()
            }
        })
        .collect()
}

fn workspace_root<'a, T>(
    manifest: &ParsedManifest,
    workspaces: &'a BTreeMap<PathBuf, T>,
) -> Option<&'a T> {
    manifest
        .path
        .parent()?
        .ancestors()
        .find_map(|directory| workspaces.get(directory))
}

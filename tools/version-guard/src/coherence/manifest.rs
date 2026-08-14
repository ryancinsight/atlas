use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use crate::error::Error;

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
    let section = sections(&text);
    let package_name = section_value(&section, "package", "name");
    let package_version_raw = section_value(&section, "package", "version");
    let package_version_workspace = section_flag(&section, "package", "version.workspace")
        || package_version_raw.as_deref() == Some("workspace = true");
    let package_version = package_version_raw.filter(|value| value != "workspace = true");
    let workspace_version = section_value(&section, "workspace.package", "version");
    let dependencies = dependency_specs_from_sections(&section, false);
    let workspace_dependencies = dependency_specs_from_sections(&section, true);
    let consumer = path
        .strip_prefix(atlas_root)
        .ok()
        .and_then(|p| p.components().nth(1))
        .map_or_else(
            || String::from("unknown"),
            |c| c.as_os_str().to_string_lossy().into_owned(),
        );
    let is_root = section.contains_key("workspace") || section.contains_key("workspace.package");
    Ok(ParsedManifest {
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
    })
}

pub(crate) fn package_index(
    manifests: &[ParsedManifest],
) -> Result<BTreeMap<String, PackageVersion>, Error> {
    let mut roots = BTreeMap::new();
    for manifest in manifests {
        if manifest.is_root {
            if let Some(version) = manifest.workspace_version.as_deref() {
                roots.insert(manifest.consumer.clone(), version.to_string());
            }
            if let (Some(name), Some(version)) = (
                manifest.package_name.as_deref(),
                manifest.package_version.as_deref(),
            ) {
                roots.insert(
                    format!("{}::{name}", manifest.consumer),
                    version.to_string(),
                );
            }
        }
    }
    let mut index: BTreeMap<String, PackageVersion> = BTreeMap::new();
    for manifest in manifests {
        let Some(name) = manifest.package_name.as_deref() else {
            continue;
        };
        let version = manifest.package_version.clone().or_else(|| {
            if manifest.package_version_workspace {
                roots.get(&manifest.consumer).cloned()
            } else {
                None
            }
        });
        if let Some(version) = version {
            if let Some(existing) = index.get(name) {
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
                index.insert(name.to_string(), PackageVersion { version });
            }
        }
    }
    Ok(index)
}

pub(crate) fn workspace_dependency_index(
    manifests: &[ParsedManifest],
) -> BTreeMap<(String, String), DependencySpec> {
    let mut result = BTreeMap::new();
    for manifest in manifests {
        if !manifest.workspace_dependencies.is_empty() {
            for dep in &manifest.workspace_dependencies {
                result.insert((manifest.consumer.clone(), dep.key.clone()), dep.clone());
            }
        }
    }
    result
}

pub(crate) fn dependency_specs(
    manifest: &ParsedManifest,
    workspace_deps: &BTreeMap<(String, String), DependencySpec>,
) -> Vec<DependencySpec> {
    manifest
        .dependencies
        .iter()
        .map(|dependency| {
            if dependency.workspace {
                workspace_deps
                    .get(&(manifest.consumer.clone(), dependency.key.clone()))
                    .cloned()
                    .unwrap_or_else(|| dependency.clone())
            } else {
                dependency.clone()
            }
        })
        .collect()
}

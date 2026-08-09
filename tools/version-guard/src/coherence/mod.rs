//! Stack-wide first-party dependency/version coherence checking.
//!
//! The coherence scan deliberately reads checked-in manifests instead of
//! invoking Cargo or contacting a registry. The Atlas meta-repository's
//! `.gitmodules` file defines the allowlist, while package manifests define
//! the current first-party package versions. This keeps the check deterministic
//! and makes those files the single sources of truth.

mod manifest;
mod member;
mod requirement;
mod toml;

use std::fmt::Write as _;
use std::path::Path;

use serde::Serialize;

use crate::error::Error;
use crate::report::Format;

use manifest::{
    ParsedManifest, dependency_specs, package_index, parse_manifest, workspace_dependency_index,
};
use member::{collect_manifests, is_first_party_source, registered_members};
use requirement::matches_requirement;

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
    #[must_use]
    pub const fn has_defect(&self) -> bool {
        !self.findings.is_empty()
    }

    fn render_human(&self) -> String {
        let mut out = format!(
            "version-guard coherence: {} manifests, {} packages, {} first-party requirements\n",
            self.manifest_count, self.package_count, self.requirement_count
        );
        if self.findings.is_empty() {
            out.push_str("version-guard coherence: clean\n");
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
        }
        let view = View {
            manifest_count: self.manifest_count,
            package_count: self.package_count,
            requirement_count: self.requirement_count,
            defect_count: self.findings.len(),
            findings: &self.findings,
        };
        serde_json::to_string(&view)
            .unwrap_or_else(|_| String::from("{\"error\":\"serialization failed\"}"))
    }
}

/// Scan all checked-in Cargo manifests under registered Atlas members.
///
/// The scan is offline and read-only. A requirement is checked only when its
/// dependency key or explicit `package =` target names an indexed first-party
/// package and the requirement contains a `version =` value. Path-only
/// dependencies are valid Cargo declarations but carry no version assertion
/// for this particular guard to evaluate.
///
/// # Errors
///
/// Returns [`Error::Manifest`](crate::Error::Manifest) when the member index,
/// a member directory, or a checked-in manifest cannot be read.
pub fn scan_atlas(atlas_root: &Path) -> Result<CoherenceReport, Error> {
    let members = registered_members(atlas_root)?;
    let mut manifests = Vec::new();
    for member in &members {
        let root_manifest = member.path.join("Cargo.toml");
        if !root_manifest.is_file() {
            return Err(Error::Manifest {
                path: root_manifest.display().to_string(),
                message: String::from("registered member has no Cargo.toml"),
            });
        }
        collect_manifests(&member.path, &mut manifests)?;
    }

    let parsed: Vec<ParsedManifest> = manifests
        .iter()
        .map(|path| parse_manifest(path, atlas_root))
        .collect::<Result<_, _>>()?;
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
            if !is_first_party_source(manifest, &dependency, &members, atlas_root) {
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
    })
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
        let report = scan_atlas(&temp).expect("scan fixture");
        assert_eq!(report.findings.len(), 1);
        assert_eq!(report.findings[0].actual, "0.1.0");
        let _ = std::fs::remove_dir_all(temp);
    }
}

use std::path::{Path, PathBuf};

use crate::CheckoutError;
use crate::graph;
use crate::manifest;

/// Inputs for one exact Atlas provider checkout.
#[derive(Debug)]
#[must_use]
pub struct CheckoutConfig {
    /// Root Cargo manifest whose external path dependencies are materialized.
    pub manifest: PathBuf,
    /// Parent directory that owns the sibling provider checkouts.
    pub destination: PathBuf,
    /// Exact 40-character Atlas commit.
    pub atlas_revision: String,
    /// Atlas Git remote. Production CI uses the public Atlas repository.
    pub atlas_remote: String,
    /// Scratch directory for the exact Atlas graph checkout.
    pub scratch: PathBuf,
}

/// Completed provider checkout summary.
#[derive(Debug, Eq, PartialEq)]
#[must_use]
pub struct CheckoutSummary {
    /// Provider repositories materialized or verified.
    pub providers: Vec<String>,
    /// Dependency manifests verified after checkout.
    pub dependency_manifests: usize,
}

/// Materializes every external sibling path dependency at its Atlas gitlink.
///
/// Existing provider directories are reused only when they are clean and
/// already at the exact recorded revision.
///
/// # Errors
///
/// Returns [`CheckoutError`] for invalid inputs, manifest or graph errors,
/// revision drift, dirty reuse, missing dependency manifests, or Git failures.
///
/// # Examples
///
/// ```no_run
/// use std::path::PathBuf;
/// use atlas_provider_checkout::{CheckoutConfig, checkout};
///
/// let summary = checkout(&CheckoutConfig {
///     manifest: PathBuf::from("consumer/Cargo.toml"),
///     destination: PathBuf::from("."),
///     atlas_revision: "0123456789abcdef0123456789abcdef01234567".to_owned(),
///     atlas_remote: "https://github.com/ryancinsight/atlas.git".to_owned(),
///     scratch: PathBuf::from("target/atlas-provider-graph"),
/// })?;
/// println!("verified {} providers", summary.providers.len());
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub fn checkout(config: &CheckoutConfig) -> Result<CheckoutSummary, CheckoutError> {
    validate_revision(&config.atlas_revision)?;
    let requirements = manifest::discover(&config.manifest, &config.destination)?;
    let atlas_root = config
        .scratch
        .join(format!("atlas-{}", config.atlas_revision));
    graph::materialize_atlas(&atlas_root, &config.atlas_remote, &config.atlas_revision)?;
    let graph = graph::load(&atlas_root, requirements.providers.keys().cloned())?;

    let mut dependency_manifests = 0;
    for (name, paths) in &requirements.providers {
        let provider = graph
            .get(name)
            .ok_or_else(|| CheckoutError::UnknownProvider(name.clone()))?;
        graph::materialize_provider(&config.destination.join(name), provider)?;
        for path in paths {
            verify_dependency_manifest(path)?;
            dependency_manifests += 1;
        }
    }

    Ok(CheckoutSummary {
        providers: requirements.providers.into_keys().collect(),
        dependency_manifests,
    })
}

fn validate_revision(revision: &str) -> Result<(), CheckoutError> {
    let is_full_sha = revision.len() == 40 && revision.bytes().all(|byte| byte.is_ascii_hexdigit());
    let is_lowercase = revision
        .bytes()
        .all(|byte| !byte.is_ascii_alphabetic() || byte.is_ascii_lowercase());
    if is_full_sha && is_lowercase {
        Ok(())
    } else {
        Err(CheckoutError::InvalidAtlasRevision(revision.to_owned()))
    }
}

fn verify_dependency_manifest(path: &Path) -> Result<(), CheckoutError> {
    let manifest = path.join("Cargo.toml");
    if manifest.is_file() {
        Ok(())
    } else {
        Err(CheckoutError::MissingDependencyManifest(manifest))
    }
}

use std::collections::BTreeMap;
use std::ffi::OsString;
use std::path::{Path, PathBuf};

use crate::CheckoutError;
use crate::git;

pub(super) struct Provider {
    pub(super) url: String,
    pub(super) revision: String,
}

pub(super) fn materialize_atlas(
    root: &Path,
    remote: &str,
    revision: &str,
) -> Result<(), CheckoutError> {
    if root.exists() {
        let current = git::output(
            Some(root),
            "read existing Atlas revision",
            git::arguments(["rev-parse", "HEAD"]),
        )?;
        if current != revision {
            return Err(CheckoutError::RevisionMismatch {
                path: root.to_path_buf(),
                expected: revision.to_owned(),
                actual: current,
            });
        }
        ensure_clean(root)?;
        return Ok(());
    }

    std::fs::create_dir_all(root).map_err(|source| CheckoutError::Io {
        path: root.to_path_buf(),
        source,
    })?;
    git::run(
        Some(root),
        "initialize Atlas graph checkout",
        git::arguments(["init", "--quiet"]),
    )?;
    git::run(
        Some(root),
        "configure Atlas graph remote",
        [
            OsString::from("remote"),
            "add".into(),
            "origin".into(),
            remote.into(),
        ],
    )?;
    fetch_exact(root, revision, "fetch Atlas graph revision")?;
    checkout_fetch_head(root, "checkout Atlas graph revision")
}

pub(super) fn load(
    atlas_root: &Path,
    names: impl Iterator<Item = String>,
) -> Result<BTreeMap<String, Provider>, CheckoutError> {
    let mut providers = BTreeMap::new();
    for name in names {
        let path = format!("repos/{name}");
        let tree_entry = git::output(
            Some(atlas_root),
            "locate Atlas provider gitlink",
            [
                OsString::from("ls-tree"),
                "HEAD".into(),
                "--".into(),
                path.clone().into(),
            ],
        )?;
        if tree_entry.is_empty() {
            return Err(CheckoutError::UnknownProvider(name));
        }
        let revision = git::output(
            Some(atlas_root),
            "read Atlas provider gitlink",
            [OsString::from("rev-parse"), format!("HEAD:{path}").into()],
        )?;
        let key = format!("submodule.{path}.url");
        let url = git::output(
            Some(atlas_root),
            "read Atlas provider URL",
            [
                OsString::from("config"),
                "--file".into(),
                ".gitmodules".into(),
                "--get".into(),
                key.into(),
            ],
        )?;
        providers.insert(name, Provider { url, revision });
    }
    Ok(providers)
}

pub(super) fn materialize_provider(path: &Path, provider: &Provider) -> Result<(), CheckoutError> {
    if path.exists() {
        let current = git::output(
            Some(path),
            "read existing provider revision",
            git::arguments(["rev-parse", "HEAD"]),
        )?;
        if current != provider.revision {
            return Err(CheckoutError::RevisionMismatch {
                path: path.to_path_buf(),
                expected: provider.revision.clone(),
                actual: current,
            });
        }
        ensure_clean(path)?;
        return Ok(());
    }

    std::fs::create_dir_all(path).map_err(|source| CheckoutError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    git::run(
        Some(path),
        "initialize provider checkout",
        git::arguments(["init", "--quiet"]),
    )?;
    git::run(
        Some(path),
        "configure provider remote",
        [
            OsString::from("remote"),
            "add".into(),
            "origin".into(),
            provider.url.clone().into(),
        ],
    )?;
    fetch_exact(path, &provider.revision, "fetch provider revision")?;
    checkout_fetch_head(path, "checkout provider revision")
}

fn fetch_exact(path: &Path, revision: &str, operation: &'static str) -> Result<(), CheckoutError> {
    git::run(
        Some(path),
        operation,
        [
            OsString::from("fetch"),
            "--depth".into(),
            "1".into(),
            "origin".into(),
            revision.into(),
        ],
    )
}

fn checkout_fetch_head(path: &Path, operation: &'static str) -> Result<(), CheckoutError> {
    git::run(
        Some(path),
        operation,
        git::arguments(["checkout", "--detach", "--quiet", "FETCH_HEAD"]),
    )
}

fn ensure_clean(path: &Path) -> Result<(), CheckoutError> {
    let status = git::output(
        Some(path),
        "inspect checkout cleanliness",
        git::arguments(["status", "--porcelain"]),
    )?;
    if status.is_empty() {
        Ok(())
    } else {
        Err(CheckoutError::DirtyCheckout(PathBuf::from(path)))
    }
}

//! End-to-end provider graph and reuse tests.

#![allow(clippy::unwrap_used)]

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};

use atlas_provider_checkout::{CheckoutConfig, CheckoutError, checkout};

static FIXTURE_ID: AtomicU64 = AtomicU64::new(0);

struct Fixture {
    root: PathBuf,
}

impl Fixture {
    fn new() -> Self {
        let id = FIXTURE_ID.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "atlas-provider-checkout-{}-{id}",
            std::process::id()
        ));
        fs::create_dir_all(&root).unwrap();
        Self { root }
    }

    fn path(&self, name: &str) -> PathBuf {
        self.root.join(name)
    }

    fn graph(&self) -> Graph {
        self.graph_with_provider_url(None)
    }

    fn graph_with_provider_url(&self, configured_url: Option<&str>) -> Graph {
        let provider = self.path("provider-origin");
        init_repository(&provider);
        write(
            &provider.join("Cargo.toml"),
            "[package]\nname = \"leto-root\"\nversion = \"0.1.0\"\nedition = \"2024\"\n",
        );
        write(
            &provider.join("crates/leto/Cargo.toml"),
            "[package]\nname = \"leto\"\nversion = \"0.1.0\"\nedition = \"2024\"\n",
        );
        commit_all(&provider, "provider");
        let provider_revision = git_output(&provider, &["rev-parse", "HEAD"]);
        let provider_url = configured_url.map_or_else(
            || provider.to_string_lossy().replace('\\', "/"),
            str::to_owned,
        );

        let atlas = self.path("atlas-origin");
        init_repository(&atlas);
        write(
            &atlas.join(".gitmodules"),
            &format!("[submodule \"repos/leto\"]\n\tpath = repos/leto\n\turl = {provider_url}\n"),
        );
        git(&atlas, &["add", ".gitmodules"]);
        git(
            &atlas,
            &[
                "update-index",
                "--add",
                "--cacheinfo",
                &format!("160000,{provider_revision},repos/leto"),
            ],
        );
        git(&atlas, &["commit", "--quiet", "-m", "atlas graph"]);
        let atlas_revision = git_output(&atlas, &["rev-parse", "HEAD"]);

        Graph {
            atlas,
            atlas_revision,
            provider,
            provider_revision,
        }
    }

    fn consumer(&self, graph: &Graph, dependency_path: &str) -> (PathBuf, CheckoutConfig) {
        self.consumer_manifest(
            graph,
            &format!(
                "[workspace]\nmembers = []\n\n[workspace.dependencies]\n\
                 leto = {{ path = \"{dependency_path}\" }}\n"
            ),
        )
    }

    fn consumer_manifest(&self, graph: &Graph, manifest: &str) -> (PathBuf, CheckoutConfig) {
        let workspace = self.path("workspace");
        let consumer = workspace.join("consumer");
        fs::create_dir_all(&consumer).unwrap();
        write(&consumer.join("Cargo.toml"), manifest);
        let config = CheckoutConfig {
            manifest: consumer.join("Cargo.toml"),
            destination: workspace.clone(),
            atlas_revision: graph.atlas_revision.clone(),
            atlas_remote: graph.atlas.to_string_lossy().into_owned(),
            scratch: self.path("scratch"),
        };
        (workspace, config)
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        if let Err(error) = fs::remove_dir_all(&self.root) {
            if std::thread::panicking() {
                return;
            }
            panic!("fixture cleanup failed at {}: {error}", self.root.display());
        }
    }
}

struct Graph {
    atlas: PathBuf,
    atlas_revision: String,
    provider: PathBuf,
    provider_revision: String,
}

#[test]
fn materializes_exact_gitlink_and_reuses_clean_checkout() {
    let fixture = Fixture::new();
    let graph = fixture.graph();
    let (workspace, config) = fixture.consumer(&graph, "../leto/crates/leto");

    let first = checkout(&config).unwrap();
    let second = checkout(&config).unwrap();

    assert_eq!(first.providers, vec!["leto"]);
    assert_eq!(first.dependency_manifests, 1);
    assert_eq!(second, first);
    assert_eq!(
        git_output(&workspace.join("leto"), &["rev-parse", "HEAD"]),
        graph.provider_revision
    );
}

#[test]
fn materializes_provider_declared_only_by_patch() {
    let fixture = Fixture::new();
    let graph = fixture.graph();
    let (workspace, config) = fixture.consumer_manifest(
        &graph,
        "[workspace]\nmembers = []\n\n\
         [patch.\"https://github.com/ryancinsight/leto\"]\n\
         leto = { path = \"../leto/crates/leto\" }\n",
    );

    let outcome = checkout(&config).unwrap();

    assert_eq!(outcome.providers, vec!["leto"]);
    assert_eq!(outcome.dependency_manifests, 1);
    assert_eq!(
        git_output(&workspace.join("leto"), &["rev-parse", "HEAD"]),
        graph.provider_revision
    );
}

#[test]
fn materializes_provider_declared_only_by_replacement() {
    let fixture = Fixture::new();
    let graph = fixture.graph();
    let (workspace, config) = fixture.consumer_manifest(
        &graph,
        "[workspace]\nmembers = []\n\n\
         [replace]\n\
         \"leto:0.1.0\" = { path = \"../leto/crates/leto\" }\n",
    );

    let outcome = checkout(&config).unwrap();

    assert_eq!(outcome.providers, vec!["leto"]);
    assert_eq!(outcome.dependency_manifests, 1);
    assert_eq!(
        git_output(&workspace.join("leto"), &["rev-parse", "HEAD"]),
        graph.provider_revision
    );
}

#[test]
fn rejects_dirty_existing_provider() {
    let fixture = Fixture::new();
    let graph = fixture.graph();
    let (workspace, config) = fixture.consumer(&graph, "../leto");
    let initial = checkout(&config).unwrap();
    write(&workspace.join("leto/untracked.txt"), "dirty");

    let error = checkout(&config).unwrap_err();

    assert_eq!(initial.providers, vec!["leto"]);
    assert!(matches!(error, CheckoutError::DirtyCheckout(_)));
}

#[test]
fn rejects_clean_existing_provider_at_wrong_revision() {
    let fixture = Fixture::new();
    let graph = fixture.graph();
    let (workspace, config) = fixture.consumer(&graph, "../leto");
    let initial = checkout(&config).unwrap();
    assert_eq!(initial.providers, vec!["leto"]);

    write(&graph.provider.join("new"), "new");
    commit_all(&graph.provider, "new provider revision");
    let wrong_revision = git_output(&graph.provider, &["rev-parse", "HEAD"]);
    let checkout_path = workspace.join("leto");
    git(
        &checkout_path,
        &["fetch", "--quiet", "origin", &wrong_revision],
    );
    git(
        &checkout_path,
        &["checkout", "--detach", "--quiet", "FETCH_HEAD"],
    );

    let error = checkout(&config).unwrap_err();

    assert!(matches!(
        error,
        CheckoutError::RevisionMismatch {
            expected,
            actual,
            ..
        } if expected == graph.provider_revision && actual == wrong_revision
    ));
}

#[test]
fn rejects_non_exact_atlas_revision_before_io() {
    let config = CheckoutConfig {
        manifest: PathBuf::from("missing/Cargo.toml"),
        destination: PathBuf::from("missing"),
        atlas_revision: "main".to_owned(),
        atlas_remote: "unused".to_owned(),
        scratch: PathBuf::from("unused"),
    };

    let error = checkout(&config).unwrap_err();

    assert!(matches!(error, CheckoutError::InvalidAtlasRevision(_)));
}

#[test]
fn rejects_external_path_outside_destination() {
    let fixture = Fixture::new();
    let workspace = fixture.path("workspace");
    let consumer = workspace.join("consumer");
    fs::create_dir_all(&consumer).unwrap();
    write(
        &consumer.join("Cargo.toml"),
        "[workspace]\nmembers = []\n\n[workspace.dependencies]\n\
         escape = { path = \"../../outside\" }\n",
    );
    let config = CheckoutConfig {
        manifest: consumer.join("Cargo.toml"),
        destination: workspace,
        atlas_revision: "0123456789abcdef0123456789abcdef01234567".to_owned(),
        atlas_remote: "unused".to_owned(),
        scratch: fixture.path("scratch"),
    };

    let error = checkout(&config).unwrap_err();

    assert!(matches!(
        error,
        CheckoutError::ExternalPathOutsideDestination { .. }
    ));
}

#[test]
fn rejects_provider_absent_from_atlas_graph() {
    let fixture = Fixture::new();
    let graph = fixture.graph();
    let (_, config) = fixture.consumer(&graph, "../unknown");

    let error = checkout(&config).unwrap_err();

    assert!(matches!(error, CheckoutError::UnknownProvider(name) if name == "unknown"));
}

#[test]
fn rejects_provider_without_submodule_url() {
    let fixture = Fixture::new();
    let graph = fixture.graph_with_provider_url(Some(""));
    let (_, config) = fixture.consumer(&graph, "../leto");

    let error = checkout(&config).unwrap_err();

    assert!(matches!(
        error,
        CheckoutError::MissingProviderUrl(name) if name == "leto"
    ));
}

fn init_repository(path: &Path) {
    fs::create_dir_all(path).unwrap();
    git(path, &["init", "--quiet"]);
    git(path, &["config", "user.name", "Atlas Test"]);
    git(path, &["config", "user.email", "atlas-test@example.com"]);
}

fn commit_all(path: &Path, message: &str) {
    git(path, &["add", "."]);
    git(path, &["commit", "--quiet", "-m", message]);
}

fn write(path: &Path, contents: &str) {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).unwrap();
    }
    fs::write(path, contents).unwrap();
}

fn git(path: &Path, arguments: &[&str]) {
    let output = Command::new("git")
        .current_dir(path)
        .args(arguments)
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "git {arguments:?} failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn git_output(path: &Path, arguments: &[&str]) -> String {
    let output = Command::new("git")
        .current_dir(path)
        .args(arguments)
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "git {arguments:?} failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8(output.stdout).unwrap().trim().to_owned()
}

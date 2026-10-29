//! Source-scoped package identities in the real manifest coherence scan.

use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicUsize, Ordering};

use atlas_version_guard::{CoherenceReport, Error, View, scan_atlas};

static NEXT_FIXTURE: AtomicUsize = AtomicUsize::new(0);

struct Fixture {
    root: PathBuf,
    modules: String,
}

impl Fixture {
    fn new() -> Self {
        let root = std::env::temp_dir().join(format!(
            "atlas-coherence-identity-{}-{}",
            std::process::id(),
            NEXT_FIXTURE.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&root).expect("fixture root");
        Self {
            root,
            modules: String::new(),
        }
    }

    fn member(&mut self, name: &str, url: &str, manifest: &str) {
        write!(
            self.modules,
            "[submodule \"repos/{name}\"]\npath = repos/{name}\nurl = {url}\n\n"
        )
        .expect("registration buffer");
        self.manifest(&format!("repos/{name}"), manifest);
        fs::write(self.root.join(".gitmodules"), &self.modules).expect("gitmodules");
    }

    fn manifest(&self, directory: &str, manifest: &str) {
        let path = self.root.join(directory);
        fs::create_dir_all(&path).expect("manifest directory");
        fs::write(path.join("Cargo.toml"), manifest).expect("manifest");
    }

    fn scan(&self) -> Result<CoherenceReport, Error> {
        scan_atlas(&self.root, View::Worktree)
    }

    fn publish_local_trees(&self) {
        for member in fs::read_dir(self.root.join("repos")).expect("members") {
            let path = member.expect("member entry").path();
            git(&path, &["init", "--quiet", "-b", "main"]);
            git(&path, &["add", "."]);
            git(&path, &["commit", "--quiet", "-m", "fixture"]);
            // The fixture's origin is its own local object store. Remote-view
            // fetching performs real Git tree reads without any network.
            git(&path, &["remote", "add", "origin", "."]);
            git(&path, &["fetch", "--quiet", "origin", "main"]);
            git(
                &path,
                &[
                    "symbolic-ref",
                    "refs/remotes/origin/HEAD",
                    "refs/remotes/origin/main",
                ],
            );
        }
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.root).expect("remove fixture");
    }
}

fn package(name: &str, version: &str) -> String {
    format!("[package]\nname = \"{name}\"\nversion = \"{version}\"\n")
}

fn git(path: &Path, args: &[&str]) {
    let output = Command::new("git")
        .arg("-C")
        .arg(path)
        .args([
            "-c",
            "user.name=Coherence Test",
            "-c",
            "user.email=coherence@atlas.test",
        ])
        .args(args)
        .output()
        .expect("local Git fixture command");
    assert!(
        output.status.success(),
        "git {args:?}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn two_providers() -> Fixture {
    let mut fixture = Fixture::new();
    fixture.member(
        "left",
        "https://example/left.git",
        &package("provider", "0.2.0"),
    );
    fixture.member(
        "right",
        "https://example/right",
        &package("provider", "0.3.0"),
    );
    fixture
}

fn assert_one_right_mismatch(report: &CoherenceReport) {
    assert_eq!(report.package_count, 3);
    assert_eq!(report.requirement_count, 2);
    assert_eq!(report.findings.len(), 1);
    let finding = &report.findings[0];
    assert_eq!(finding.consumer, "consumer");
    assert_eq!(finding.dependency, "right");
    assert_eq!(finding.package, "provider");
    assert_eq!(finding.required, "0.2.0");
    assert_eq!(finding.actual, "0.3.0");
    assert!(report.has_defect());
}

#[test]
fn repository_local_helpers_keep_independent_versions() {
    // No source URLs is also supported by existing path-only Atlas fixtures:
    // an absent URL must not collapse every member into one empty identity.
    for urls in [["https://example/alpha", "https://example/beta"], ["", ""]] {
        let mut fixture = Fixture::new();
        fixture.member("alpha", urls[0], &package("alpha", "1.0.0"));
        fixture.member("beta", urls[1], &package("beta", "1.0.0"));
        fixture.manifest("repos/alpha/xtask", &package("xtask", "0.1.0"));
        fixture.manifest("repos/beta/xtask", &package("xtask", "0.1.1"));
        let report = fixture.scan().expect("independent helper versions");
        assert_eq!(report.manifest_count, 4);
        assert_eq!(report.package_count, 4);
        assert_eq!(report.requirement_count, 0);
        assert_eq!(report.findings, []);
        assert!(!report.has_defect());
    }
}

#[test]
fn path_aliases_compare_the_selected_provider_and_preserve_mismatches() {
    let mut fixture = two_providers();
    fixture.member(
        "consumer", "https://example/consumer",
        &(package("consumer", "1.0.0") + "[dependencies]\nleft = { package = \"provider\", path = \"../left\", version = \"0.2.0\" }\nright = { package = \"provider\", path = \"../right\", version = \"0.2.0\" }\n"),
    );
    assert_one_right_mismatch(&fixture.scan().expect("path provider identities"));
}

#[test]
fn git_aliases_compare_the_selected_provider_and_preserve_mismatches() {
    let mut fixture = two_providers();
    fixture.member(
        "consumer", "https://example/consumer",
        &(package("consumer", "1.0.0") + "[dependencies]\nleft = { package = \"provider\", git = \"HTTPS://EXAMPLE/LEFT.git\", version = \"0.2.0\" }\nright = { package = \"provider\", git = \"https://example/right.git\", version = \"0.2.0\" }\n"),
    );
    assert_one_right_mismatch(&fixture.scan().expect("git provider identities"));
}

#[test]
fn inherited_path_is_relative_to_its_workspace_declaration() {
    let mut fixture = two_providers();
    fixture.member(
        "consumer", "https://example/consumer",
        "[workspace]\nmembers = [\"crates/client\"]\n[workspace.package]\nversion = \"1.0.0\"\n[workspace.dependencies]\nright = { package = \"provider\", path = \"../right\", version = \"0.2.0\" }\n",
    );
    fixture.manifest(
        "repos/consumer/crates/client",
        "[package]\nname = \"client\"\nversion.workspace = true\n[dependencies]\nright.workspace = true\n",
    );
    let report = fixture.scan().expect("inherited provider identity");
    assert_eq!(report.package_count, 3);
    assert_eq!(report.requirement_count, 1);
    assert_eq!(report.findings.len(), 1);
    assert_eq!(
        report.findings[0].manifest,
        Path::new("repos/consumer/crates/client/Cargo.toml")
            .display()
            .to_string()
    );
    assert_eq!(report.findings[0].dependency, "right");
    assert_eq!(report.findings[0].actual, "0.3.0");
    assert_eq!(report.findings[0].required, "0.2.0");
}

#[test]
fn conflicting_versions_within_one_provider_still_fail_closed() {
    let mut fixture = Fixture::new();
    fixture.member(
        "provider",
        "https://example/provider",
        &package("provider", "0.2.0"),
    );
    fixture.manifest("repos/provider/duplicate", &package("provider", "0.3.0"));
    let error = fixture
        .scan()
        .expect_err("same provider cannot have conflicting versions");
    let Error::Manifest { path, message } = error else {
        panic!("expected package identity error, got {error}");
    };
    assert!(path.ends_with("repos/provider/duplicate/Cargo.toml"));
    assert!(message.contains("provider"));
    assert!(message.contains("0.2.0") && message.contains("0.3.0"));
}

#[test]
fn duplicate_registrations_of_one_git_source_do_not_hide_version_conflicts() {
    let mut fixture = Fixture::new();
    fixture.member(
        "first",
        "https://example/provider.git",
        &package("provider", "0.2.0"),
    );
    fixture.member(
        "second",
        "HTTPS://EXAMPLE/PROVIDER",
        &package("provider", "0.3.0"),
    );
    let error = fixture
        .scan()
        .expect_err("canonical source still conflicts");
    let Error::Manifest { path, message } = error else {
        panic!("expected canonical source error, got {error}");
    };
    assert!(path.ends_with("repos/second/Cargo.toml"));
    assert!(message.contains("provider"));
    assert!(message.contains("0.2.0") && message.contains("0.3.0"));
}

#[test]
fn registry_only_collision_does_not_become_a_first_party_edge() {
    let mut fixture = Fixture::new();
    fixture.member(
        "provider",
        "https://example/provider",
        &package("provider", "0.3.0"),
    );
    fixture.member(
        "consumer",
        "https://example/consumer",
        &(package("consumer", "1.0.0") + "[dependencies]\nprovider = \"0.2.0\"\n"),
    );
    let report = fixture.scan().expect("registry-only edge");
    assert_eq!(report.package_count, 2);
    assert_eq!(report.requirement_count, 0);
    assert_eq!(report.findings, []);
}

#[test]
fn absent_package_in_selected_source_never_falls_back_to_another_provider() {
    let mut fixture = Fixture::new();
    fixture.member(
        "left",
        "https://example/left",
        &package("provider", "0.2.0"),
    );
    fixture.member("right", "https://example/right", &package("other", "0.7.0"));
    fixture.member("consumer", "https://example/consumer", &(package("consumer", "1.0.0") + "[dependencies]\nprovider = { git = \"https://example/right\", version = \"0.2.0\" }\n"));
    let report = fixture.scan().expect("source-scoped missing package");
    assert_eq!(report.package_count, 3);
    assert_eq!(report.requirement_count, 0);
    assert_eq!(report.findings, []);
}

#[test]
fn remote_tree_paths_bind_duplicate_names_without_materialized_targets() {
    let mut fixture = two_providers();
    fixture.manifest("repos/right/new-crate", &package("new-provider", "0.4.0"));
    fixture.member("consumer", "https://example/consumer", &(package("consumer", "1.0.0") + "[dependencies]\nleft = { package = \"provider\", path = \"../left\", version = \"0.2.0\" }\nright = { package = \"provider\", path = \"../right\", version = \"0.2.0\" }\nnew-provider = { path = \"../right/new-crate\", version = \"0.3.0\" }\n"));
    fixture.publish_local_trees();
    fs::remove_dir_all(fixture.root.join("repos/right/new-crate")).expect("unmaterialized target");
    let report = scan_atlas(&fixture.root, View::Remotes).expect("source-scoped remote tree scan");
    assert_eq!(report.package_count, 4);
    assert_eq!(report.requirement_count, 3);
    assert_eq!(report.findings.len(), 2);
    assert!(report.unmeasured.is_empty());
    assert_eq!(report.findings[0].dependency, "new-provider");
    assert_eq!(report.findings[0].actual, "0.4.0");
    assert_eq!(report.findings[1].dependency, "right");
    assert_eq!(report.findings[1].actual, "0.3.0");
}

#[test]
fn nested_workspace_uses_its_own_dependency_and_package_version() {
    let mut fixture = Fixture::new();
    fixture.member(
        "provider",
        "https://example/provider",
        &package("provider", "0.3.0"),
    );
    fixture.member("consumer", "https://example/consumer", "[workspace]\nmembers = [\"crates/client\"]\nexclude = [\"tools\"]\n[workspace.package]\nversion = \"1.0.0\"\n[workspace.dependencies]\nprovider = { path = \"../provider\", version = \"0.2.0\" }\n");
    fixture.manifest("repos/consumer/crates/client", "[package]\nname = \"client\"\nversion.workspace = true\n[dependencies]\nprovider.workspace = true\n");
    fixture.manifest("repos/consumer/tools", "[workspace]\nmembers = [\"helper\"]\n[workspace.package]\nversion = \"2.0.0\"\n[workspace.dependencies]\nprovider = { path = \"../../provider\", version = \"0.3.0\" }\n");
    fixture.manifest("repos/consumer/tools/helper", "[package]\nname = \"helper\"\nversion.workspace = true\n[dependencies]\nprovider.workspace = true\n");
    fixture.member("observer", "https://example/observer", &(package("observer", "1.0.0") + "[dependencies]\nclient = { path = \"../consumer/crates/client\", version = \"1.0.0\" }\nhelper = { path = \"../consumer/tools/helper\", version = \"2.0.0\" }\n"));
    let report = fixture.scan().expect("nearest workspace declarations");
    assert_eq!(report.package_count, 4);
    assert_eq!(report.requirement_count, 4);
    assert_eq!(report.findings.len(), 1);
    assert_eq!(
        report.findings[0].manifest,
        Path::new("repos/consumer/crates/client/Cargo.toml")
            .display()
            .to_string()
    );
    assert_eq!(report.findings[0].actual, "0.3.0");
    assert_eq!(report.findings[0].required, "0.2.0");
}

#[test]
fn empty_inner_workspace_does_not_inherit_an_outer_dependency() {
    for inner_root in [
        "[workspace]\nmembers = [\"helper\"]\n",
        "[workspace.metadata]\nowner = \"helper\"\n",
    ] {
        let mut fixture = Fixture::new();
        fixture.member(
            "provider",
            "https://example/provider",
            &package("provider", "0.3.0"),
        );
        fixture.member("consumer", "https://example/consumer", "[workspace]\nexclude = [\"tools\"]\n[workspace.dependencies]\nprovider = { path = \"../provider\", version = \"0.2.0\" }\n");
        fixture.manifest("repos/consumer/tools", inner_root);
        fixture.manifest(
            "repos/consumer/tools/helper",
            &(package("helper", "1.0.0") + "[dependencies]\nprovider.workspace = true\n"),
        );
        let report = fixture
            .scan()
            .expect("unknown inherited dependency stays unmeasured");
        assert_eq!(report.package_count, 2);
        assert_eq!(report.requirement_count, 0);
        assert_eq!(report.findings, []);
    }
}

#[test]
fn implicit_workspace_table_keeps_inherited_dependency_checks() {
    let mut fixture = Fixture::new();
    fixture.member(
        "provider",
        "https://example/provider",
        &package("provider", "0.3.0"),
    );
    fixture.member("consumer", "https://example/consumer", &(package("consumer", "1.0.0") + "[dependencies]\nhelper = { path = \"helper\" }\n[workspace.dependencies]\nprovider = { git = \"https://example/provider\", version = \"0.2.0\" }\n"));
    fixture.manifest(
        "repos/consumer/helper",
        &(package("helper", "1.0.0") + "[dependencies]\nprovider.workspace = true\n"),
    );
    let report = fixture.scan().expect("implicit workspace root");
    assert_eq!(report.package_count, 3);
    assert_eq!(report.requirement_count, 1);
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.findings[0].consumer, "consumer");
    assert_eq!(report.findings[0].dependency, "provider");
    assert_eq!(report.findings[0].actual, "0.3.0");
    assert_eq!(report.findings[0].required, "0.2.0");
}

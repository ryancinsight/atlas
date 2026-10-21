use super::*;

#[test]
fn injected_backward_fixture_is_reported() {
    let temp = std::env::temp_dir().join(format!("atlas-version-coherence-{}", std::process::id()));
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
    let report = scan_atlas(&temp, View::Worktree).expect("scan fixture");
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.findings[0].actual, "0.1.0");
    let _ = std::fs::remove_dir_all(temp);
}

#[test]
fn remotes_view_sees_a_provider_bump_the_pinned_trees_hide() {
    // The failure this view exists for: a provider publishes a break on its
    // default branch while every gitlink-pinned checkout still satisfies the
    // consumer's requirement, so the working-tree scan is clean. A submodule
    // cloned at a gitlink has no `origin/HEAD`, which is exactly why
    // `stale_members` cannot fall back to the remote there.
    let temp = scratch("remotes");
    let root = temp.join("atlas");

    // Provider history: 0.5.0 (the pin) then 0.6.0 (the published tip).
    let provider_upstream = temp.join("provider-upstream");
    std::fs::create_dir_all(&provider_upstream).expect("provider upstream");
    git(&provider_upstream, &["init", "-b", "main"]);
    write_package(&provider_upstream, "provider", "0.5.0");
    git(&provider_upstream, &["add", "."]);
    git(&provider_upstream, &["commit", "-m", "0.5.0"]);
    let pinned = git(&provider_upstream, &["rev-parse", "HEAD"]).expect("pinned sha");
    write_package(&provider_upstream, "provider", "0.6.0");
    git(&provider_upstream, &["add", "."]);
    git(&provider_upstream, &["commit", "-m", "0.6.0"]);

    // Consumer expects ^0.5.0 and is not swept.
    let consumer_upstream = temp.join("consumer-upstream");
    std::fs::create_dir_all(&consumer_upstream).expect("consumer upstream");
    git(&consumer_upstream, &["init", "-b", "main"]);
    std::fs::write(
        consumer_upstream.join("Cargo.toml"),
        "[package]\nname = \"consumer\"\nversion = \"0.1.0\"\n[dependencies]\nprovider = { package = \"provider\", version = \"0.5.0\", git = \"https://example/provider\" }\n",
    )
    .expect("consumer manifest");
    git(&consumer_upstream, &["add", "."]);
    git(&consumer_upstream, &["commit", "-m", "consumer"]);

    std::fs::create_dir_all(root.join("repos")).expect("repos dir");
    std::fs::write(
        root.join(".gitmodules"),
        "[submodule \"repos/provider\"]\n\tpath = repos/provider\n\turl = https://example/provider\n\n[submodule \"repos/consumer\"]\n\tpath = repos/consumer\n\turl = https://example/consumer\n",
    )
    .expect("gitmodules");

    // Both members are gitlink-shaped: fetch the tip, check out a detached
    // commit, and never create `origin/HEAD`.
    let provider = root.join("repos").join("provider");
    std::fs::create_dir_all(&provider).expect("provider dir");
    git(&provider, &["init", "-b", "main"]);
    git(
        &provider,
        &["remote", "add", "origin", &file_url(&provider_upstream)],
    );
    git(&provider, &["fetch", "--quiet", "origin", "main"]);
    git(&provider, &["checkout", "--quiet", "--detach", &pinned]);

    let consumer = root.join("repos").join("consumer");
    std::fs::create_dir_all(&consumer).expect("consumer dir");
    git(&consumer, &["init", "-b", "main"]);
    git(
        &consumer,
        &["remote", "add", "origin", &file_url(&consumer_upstream)],
    );
    git(&consumer, &["fetch", "--quiet", "origin", "main"]);
    let _ = git(
        &consumer,
        &["checkout", "--quiet", "--detach", "origin/main"],
    );

    // The recorded state is coherent: the pinned provider satisfies ^0.5.0.
    let worktree = scan_atlas(&root, View::Worktree).expect("worktree scan");
    assert_eq!(
        worktree.findings.len(),
        0,
        "the pinned trees satisfy the requirement, so the working-tree view is clean"
    );

    // The published state is not: the provider now publishes 0.6.0.
    let remotes = scan_atlas(&root, View::Remotes).expect("remotes scan");
    assert!(
        remotes.unmeasured.is_empty(),
        "both members must resolve: {:?}",
        remotes.unmeasured
    );
    assert_eq!(
        remotes.findings.len(),
        1,
        "the provider bump must be reported"
    );
    assert_eq!(remotes.findings[0].package, "provider");
    assert_eq!(remotes.findings[0].actual, "0.6.0");
    assert!(remotes.has_defect());

    let _ = std::fs::remove_dir_all(&temp);
}

fn write_package(repo: &Path, name: &str, version: &str) {
    std::fs::write(
        repo.join("Cargo.toml"),
        format!("[package]\nname = \"{name}\"\nversion = \"{version}\"\n"),
    )
    .expect("package manifest");
}

/// A local path usable as a git remote URL on Windows (forward slashes).
fn file_url(path: &Path) -> String {
    path.to_string_lossy().replace('\\', "/")
}

#[test]
fn read_manifest_prefers_origin_over_a_stale_working_tree() {
    // The gaia 0.4.0 → 0.5.0 case: the bump sits on origin while a checkout
    // is still behind. read_manifest, given the member's origin commit,
    // must parse the origin manifest (0.5.0), not the stale worktree
    // (0.4.0) — a coherence verdict against the worktree would compare
    // against a version the stack no longer publishes.
    let temp = scratch("origin-read");
    let upstream = temp.join("upstream");
    std::fs::create_dir_all(&upstream).expect("upstream dir");
    git(&upstream, &["init", "-b", "main"]);
    write_git_member(&upstream, "0.4.0");
    git(&upstream, &["add", "."]);
    git(&upstream, &["commit", "-m", "bump to 0.4.0"]);

    // Clone at 0.4.0, then advance origin to 0.5.0 so the checkout is
    // behind its own bump.
    let member = temp.join("repos").join("member");
    std::fs::create_dir_all(temp.join("repos")).expect("repos dir");
    clone(&upstream, &member);
    write_git_member(&upstream, "0.5.0");
    git(&upstream, &["add", "."]);
    git(&upstream, &["commit", "-m", "bump to 0.5.0"]);
    git(&member, &["fetch", "--quiet", "origin"]);
    let origin_commit = git(&member, &["rev-parse", "origin/main"]).expect("origin tip");

    let manifest_path = member.join("Cargo.toml");
    let mut origin_map = BTreeMap::new();
    origin_map.insert(member.clone(), origin_commit);

    let parsed = read_manifest(&manifest_path, &temp, &origin_map).expect("read manifest");
    // origin publishes 0.5.0, so the parsed package version is 0.5.0 — not
    // the stale 0.4.0 the working tree carries.
    assert_eq!(parsed.package_version.as_deref(), Some("0.5.0"));

    // Without the origin map the same manifest reads the stale worktree.
    let parsed = read_manifest(&manifest_path, &temp, &BTreeMap::new()).expect("read manifest");
    assert_eq!(parsed.package_version.as_deref(), Some("0.4.0"));

    let _ = std::fs::remove_dir_all(&temp);
}

fn git(repo: &Path, args: &[&str]) -> Option<String> {
    Command::new("git")
        .arg("-C")
        .arg(repo)
        .arg("-c")
        .arg("user.email=guard@atlas.test")
        .arg("-c")
        .arg("user.name=Guard Test")
        .args(args)
        .output()
        .ok()
        .filter(|out| out.status.success())
        .map(|out| String::from_utf8_lossy(&out.stdout).trim().to_owned())
}

fn clone(from: &Path, to: &Path) {
    assert!(
        Command::new("git")
            .args(["clone", "--quiet"])
            .arg(from)
            .arg(to)
            .output()
            .is_ok_and(|out| out.status.success()),
        "git clone {from:?} -> {to:?} failed"
    );
}

fn scratch(name: &str) -> PathBuf {
    let root = std::env::temp_dir().join(format!(
        "atlas-version-coherence-{name}-{}-{:?}",
        std::process::id(),
        std::thread::current().id()
    ));
    let _ = std::fs::remove_dir_all(&root);
    std::fs::create_dir_all(&root).expect("scratch root");
    root
}

fn write_git_member(repo: &Path, version: &str) {
    std::fs::write(
        repo.join("Cargo.toml"),
        format!(
            "[workspace]\nmembers = [\".\"]\n[workspace.package]\nversion = \"{version}\"\n[package]\nname = \"member\"\nversion = \"{version}\"\n"
        ),
    )
    .expect("member manifest");
}

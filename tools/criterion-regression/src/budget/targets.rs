use std::path::{Path, PathBuf};
use std::process::Command;

use serde::Deserialize;

use super::Mode;
use super::error::BudgetError;

/// Executable produced by the unbounded compile phase.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PreparedTarget {
    /// Package that owns the target.
    pub package: String,
    /// Target name (`--bench`/`--example` identity).
    pub name: String,
    /// Compiled binary to execute under the bound.
    pub executable: PathBuf,
}

/// Workspace facts the runner needs from `cargo metadata`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkspaceLayout {
    /// Directory the child processes run in.
    pub workspace_root: PathBuf,
    /// Resolved shared target directory; exported to children so a directly
    /// executed Criterion binary writes below it instead of minting a local
    /// `target/` (one build cache per stack).
    pub target_directory: PathBuf,
}

#[derive(Deserialize)]
struct Metadata {
    workspace_root: PathBuf,
    target_directory: PathBuf,
}

/// Queries `cargo metadata` for the workspace root and target directory.
pub fn workspace_layout(manifest_path: &Path) -> Result<WorkspaceLayout, BudgetError> {
    let output = Command::new("cargo")
        .args([
            "metadata",
            "--no-deps",
            "--format-version",
            "1",
            "--manifest-path",
        ])
        .arg(manifest_path)
        .output()
        .map_err(|source| BudgetError::Metadata {
            manifest_path: manifest_path.to_path_buf(),
            stderr: source.to_string(),
        })?;
    if !output.status.success() {
        return Err(BudgetError::Metadata {
            manifest_path: manifest_path.to_path_buf(),
            stderr: String::from_utf8_lossy(&output.stderr).trim().to_owned(),
        });
    }
    let metadata: Metadata = serde_json::from_slice(&output.stdout)
        .map_err(|source| BudgetError::MetadataJson { source })?;
    Ok(WorkspaceLayout {
        workspace_root: metadata.workspace_root,
        target_directory: metadata.target_directory,
    })
}

#[derive(Deserialize)]
struct ArtifactMessage<'a> {
    reason: &'a str,
    #[serde(default)]
    package_id: String,
    #[serde(default)]
    target: Option<ArtifactTarget>,
    #[serde(default)]
    executable: Option<PathBuf>,
}

#[derive(Deserialize)]
struct ArtifactTarget {
    name: String,
    kind: Vec<String>,
}

/// Compiles every target of the mode's kind and returns their executables.
///
/// The compile phase is deliberately unbounded: build cost is a property of
/// the shared cache state, not of the artifact under budget, and must never
/// be misattributed to the runtime bound.
pub fn compile_targets(
    manifest_path: &Path,
    mode: Mode,
) -> Result<Vec<PreparedTarget>, BudgetError> {
    let mut command = Command::new("cargo");
    match mode {
        Mode::Smoke | Mode::Timing => {
            command.args(["bench", "--benches", "--no-run"]);
        }
        Mode::Examples => {
            command.args(["build", "--examples"]);
        }
    }
    command
        .args(["--message-format", "json", "--manifest-path"])
        .arg(manifest_path);
    let output = command.output().map_err(|source| BudgetError::Compile {
        code: None,
        stderr: source.to_string(),
    })?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let tail: Vec<&str> = stderr.trim().lines().rev().take(20).collect();
        let tail: Vec<&str> = tail.into_iter().rev().collect();
        return Err(BudgetError::Compile {
            code: output.status.code(),
            stderr: tail.join("\n"),
        });
    }
    parse_artifacts(&output.stdout, mode.target_kind())
}

fn parse_artifacts(stdout: &[u8], kind: &str) -> Result<Vec<PreparedTarget>, BudgetError> {
    let mut prepared = Vec::new();
    for line in stdout.split(|byte| *byte == b'\n') {
        if line.is_empty() {
            continue;
        }
        let message: ArtifactMessage<'_> =
            serde_json::from_slice(line).map_err(|source| BudgetError::ArtifactJson { source })?;
        if message.reason != "compiler-artifact" {
            continue;
        }
        let (Some(target), Some(executable)) = (message.target, message.executable) else {
            continue;
        };
        if !target.kind.iter().any(|entry| entry == kind) {
            continue;
        }
        prepared.push(PreparedTarget {
            package: package_name(&message.package_id).to_owned(),
            name: target.name,
            executable,
        });
    }
    prepared.sort_by(|a, b| (&a.package, &a.name).cmp(&(&b.package, &b.name)));
    prepared.dedup();
    Ok(prepared)
}

/// Extracts the package name from a package-id spec: the URL fragment carries
/// `name@version` when the name differs from the source directory, a bare
/// version otherwise, in which case the name is the last path segment.
fn package_name(package_id: &str) -> &str {
    match package_id.rsplit_once('#') {
        Some((path, fragment)) => match fragment.rsplit_once('@') {
            Some((name, _version)) => name,
            None => path.rsplit('/').next().unwrap_or(path),
        },
        None => package_id,
    }
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;

    #[test]
    fn extracts_bench_artifacts_with_executables() {
        let stdout = concat!(
            r#"{"reason":"compiler-artifact","package_id":"path+file:///d/atlas/repos/themis#themis@0.3.1","target":{"name":"laws","kind":["bench"]},"executable":"D:/atlas/target/release/deps/laws-abc.exe"}"#,
            "\n",
            r#"{"reason":"compiler-artifact","package_id":"path+file:///d/atlas/repos/themis#themis@0.3.1","target":{"name":"themis","kind":["lib"]},"executable":null}"#,
            "\n",
            r#"{"reason":"build-finished","success":true}"#,
            "\n",
        )
        .as_bytes()
        .to_vec();

        let prepared = parse_artifacts(&stdout, "bench").unwrap();

        assert_eq!(
            prepared,
            vec![PreparedTarget {
                package: "themis".to_owned(),
                name: "laws".to_owned(),
                executable: PathBuf::from("D:/atlas/target/release/deps/laws-abc.exe"),
            }]
        );
    }

    #[test]
    fn package_name_handles_both_package_id_spec_shapes() {
        assert_eq!(
            package_name("path+file:///d/atlas/repos/themis#0.3.1"),
            "themis"
        );
        assert_eq!(
            package_name("path+file:///d/atlas/repos/kwavers#kwavers-driver@0.9.0"),
            "kwavers-driver"
        );
    }

    #[test]
    fn example_kind_filters_out_bench_artifacts() {
        let stdout = concat!(
            r#"{"reason":"compiler-artifact","package_id":"a#pkg@1.0.0","target":{"name":"demo","kind":["example"]},"executable":"/t/demo"}"#,
            "\n",
            r#"{"reason":"compiler-artifact","package_id":"a#pkg@1.0.0","target":{"name":"laws","kind":["bench"]},"executable":"/t/laws"}"#,
            "\n",
        )
        .as_bytes()
        .to_vec();

        let prepared = parse_artifacts(&stdout, "example").unwrap();

        assert_eq!(
            prepared,
            vec![PreparedTarget {
                package: "pkg".to_owned(),
                name: "demo".to_owned(),
                executable: PathBuf::from("/t/demo"),
            }]
        );
    }
}

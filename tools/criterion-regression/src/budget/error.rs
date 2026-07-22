use std::error::Error;
use std::fmt::{self, Display, Formatter};
use std::io;
use std::path::PathBuf;

/// Failure to discover, build, or execute a budgeted target.
#[derive(Debug)]
#[non_exhaustive]
pub enum BudgetError {
    /// The requested wall-clock bound is zero.
    ZeroBound,
    /// `cargo metadata` could not be spawned or exited unsuccessfully.
    Metadata {
        /// Manifest the metadata query was issued for.
        manifest_path: PathBuf,
        /// Captured standard error, trimmed.
        stderr: String,
    },
    /// `cargo metadata` output was not the expected JSON shape.
    MetadataJson {
        /// Underlying JSON error.
        source: serde_json::Error,
    },
    /// The unbounded compile phase failed; no budget was evaluated.
    Compile {
        /// Exit code of the compile invocation when one exists.
        code: Option<i32>,
        /// Captured standard error, trimmed to its tail.
        stderr: String,
    },
    /// A compile-phase artifact message was not the expected JSON shape.
    ArtifactJson {
        /// Underlying JSON error.
        source: serde_json::Error,
    },
    /// A target executable could not be spawned.
    Spawn {
        /// Name of the target whose executable failed to start.
        target: String,
        /// Executable path that failed to spawn.
        executable: PathBuf,
        /// Underlying operating-system error.
        source: io::Error,
    },
    /// An operating-system wait or kill operation failed mid-enforcement.
    Supervise {
        /// Name of the target being supervised.
        target: String,
        /// Underlying operating-system error.
        source: io::Error,
    },
}

impl Display for BudgetError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        match self {
            Self::ZeroBound => {
                write!(
                    formatter,
                    "wall-clock bound must be a positive number of seconds"
                )
            }
            Self::Metadata {
                manifest_path,
                stderr,
            } => {
                write!(
                    formatter,
                    "cargo metadata failed for {}: {stderr}",
                    manifest_path.display()
                )
            }
            Self::MetadataJson { source } => {
                write!(formatter, "cargo metadata emitted invalid JSON: {source}")
            }
            Self::Compile { code, stderr } => match code {
                Some(code) => {
                    write!(
                        formatter,
                        "compile phase failed with exit code {code}: {stderr}"
                    )
                }
                None => write!(formatter, "compile phase was terminated: {stderr}"),
            },
            Self::ArtifactJson { source } => {
                write!(
                    formatter,
                    "compile phase emitted invalid artifact JSON: {source}"
                )
            }
            Self::Spawn {
                target,
                executable,
                source,
            } => {
                write!(
                    formatter,
                    "failed to spawn {target} ({}): {source}",
                    executable.display()
                )
            }
            Self::Supervise { target, source } => {
                write!(formatter, "failed to supervise {target}: {source}")
            }
        }
    }
}

impl Error for BudgetError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::MetadataJson { source } | Self::ArtifactJson { source } => Some(source),
            Self::Spawn { source, .. } | Self::Supervise { source, .. } => Some(source),
            Self::ZeroBound | Self::Metadata { .. } | Self::Compile { .. } => None,
        }
    }
}

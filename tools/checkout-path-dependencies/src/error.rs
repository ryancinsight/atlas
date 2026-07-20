use std::error::Error;
use std::fmt::{self, Display, Formatter};
use std::io;
use std::path::PathBuf;
use std::process::ExitStatus;

/// Failure to resolve or check out an Atlas path dependency.
#[derive(Debug)]
#[non_exhaustive]
pub enum CheckoutError {
    /// The requested Atlas reference is not a full lowercase hexadecimal SHA.
    InvalidAtlasRevision(String),
    /// A required input path does not exist or has the wrong kind.
    InvalidPath {
        /// Invalid path.
        path: PathBuf,
        /// Required path property.
        requirement: &'static str,
    },
    /// A path dependency escapes the authorized destination.
    ExternalPathOutsideDestination {
        /// Dependency path declared in Cargo.toml.
        dependency: PathBuf,
        /// Authorized provider destination.
        destination: PathBuf,
    },
    /// A path dependency names no provider below the destination.
    MissingProviderName(PathBuf),
    /// A required provider is absent from the Atlas graph.
    UnknownProvider(String),
    /// A provider checkout exists at the wrong revision.
    RevisionMismatch {
        /// Existing provider checkout.
        path: PathBuf,
        /// Atlas-recorded revision.
        expected: String,
        /// Existing checkout revision.
        actual: String,
    },
    /// A reusable checkout contains modified or untracked content.
    DirtyCheckout(PathBuf),
    /// A required dependency manifest is absent after checkout.
    MissingDependencyManifest(PathBuf),
    /// A filesystem operation failed.
    Io {
        /// Path involved in the operation.
        path: PathBuf,
        /// Underlying error.
        source: io::Error,
    },
    /// A Cargo manifest is invalid TOML.
    Toml {
        /// Invalid manifest.
        path: PathBuf,
        /// Parser diagnostic.
        source: toml::de::Error,
    },
    /// A Git command failed.
    Git {
        /// Human-readable operation.
        operation: &'static str,
        /// Process status.
        status: ExitStatus,
        /// Standard error emitted by Git.
        stderr: String,
    },
    /// Git emitted bytes that are not UTF-8.
    GitOutput {
        /// Human-readable operation.
        operation: &'static str,
        /// UTF-8 diagnostic.
        source: std::string::FromUtf8Error,
    },
}

impl Display for CheckoutError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidAtlasRevision(revision) => {
                write!(
                    formatter,
                    "Atlas revision must be 40 lowercase hex digits: {revision:?}"
                )
            }
            Self::InvalidPath { path, requirement } => {
                write!(formatter, "{} must be {requirement}", path.display())
            }
            Self::ExternalPathOutsideDestination {
                dependency,
                destination,
            } => write!(
                formatter,
                "path dependency {} is outside provider destination {}",
                dependency.display(),
                destination.display()
            ),
            Self::MissingProviderName(path) => {
                write!(
                    formatter,
                    "path dependency has no provider component: {}",
                    path.display()
                )
            }
            Self::UnknownProvider(provider) => {
                write!(formatter, "Atlas has no recorded provider repos/{provider}")
            }
            Self::RevisionMismatch {
                path,
                expected,
                actual,
            } => write!(
                formatter,
                "{} is at {actual}, expected Atlas gitlink {expected}",
                path.display()
            ),
            Self::DirtyCheckout(path) => {
                write!(formatter, "provider checkout is dirty: {}", path.display())
            }
            Self::MissingDependencyManifest(path) => {
                write!(
                    formatter,
                    "dependency manifest is missing: {}",
                    path.display()
                )
            }
            Self::Io { path, source } => {
                write!(
                    formatter,
                    "filesystem operation failed at {}: {source}",
                    path.display()
                )
            }
            Self::Toml { path, source } => {
                write!(
                    formatter,
                    "invalid Cargo manifest {}: {source}",
                    path.display()
                )
            }
            Self::Git {
                operation,
                status,
                stderr,
            } => write!(
                formatter,
                "{operation} failed with {status}: {}",
                stderr.trim()
            ),
            Self::GitOutput { operation, source } => {
                write!(formatter, "{operation} emitted invalid UTF-8: {source}")
            }
        }
    }
}

impl Error for CheckoutError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Io { source, .. } => Some(source),
            Self::Toml { source, .. } => Some(source),
            Self::GitOutput { source, .. } => Some(source),
            _ => None,
        }
    }
}

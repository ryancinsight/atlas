//! Typed errors for the manifest-version guard.
//!
//! Mirrors the shape of `tools/gitlink-coherence/src/error.rs`: a single enum
//! carrying one variant per failure mode the guard can encounter, with
//! `#[from]` impls for the underlying I/O failure and a `Display` that names
//! the violated invariant without restating a source message.

use std::fmt;
use std::io;

/// Errors raised by the manifest-version guard.
#[derive(Debug)]
pub enum Error {
    /// A `git diff` invocation failed (non-zero exit, missing rev, etc.).
    Git {
        /// The command whose execution failed, e.g. `git diff <range> -- '*.toml'`.
        command: String,
        /// The captured stderr from the failed command.
        stderr: String,
    },
    /// A `--commit-msg <path>` argument could not be read.
    Io(io::Error),
    /// The `--format` argument did not name a recognised output format.
    Format {
        /// The invalid value the caller supplied.
        value: String,
    },
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Git { command, stderr } => {
                let stderr_trim = stderr.trim();
                if stderr_trim.is_empty() {
                    write!(f, "git command failed: `{command}` (no stderr)")
                } else {
                    write!(f, "git command failed: `{command}`: {stderr_trim}")
                }
            }
            Self::Io(source) => write!(f, "I/O error reading --commit-msg path: {source}"),
            Self::Format { value } => {
                write!(
                    f,
                    "unrecognised --format value `{value}` (expected: human | json)"
                )
            }
        }
    }
}

impl std::error::Error for Error {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io(source) => Some(source),
            Self::Git { .. } | Self::Format { .. } => None,
        }
    }
}

impl From<io::Error> for Error {
    fn from(source: io::Error) -> Self {
        Self::Io(source)
    }
}

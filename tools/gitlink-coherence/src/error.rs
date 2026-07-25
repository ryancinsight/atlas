//! Typed errors raised by the gitlink coherence auditor.

use std::error::Error as StdError;
use std::fmt;
use std::io;

/// The kind of failure raised by the auditor.
///
/// Each variant names the violated invariant or the failing external
/// interaction; the [`Display`](fmt::Display) implementation carries only the
/// new context for that layer, never restating the source chain. Source
/// chaining preserves the underlying cause for diagnostic reporters.
#[derive(Debug)]
pub enum Error {
    /// The supplied atlas-meta root does not contain a readable `.gitmodules`.
    MissingGitmodules(io::Error),
    /// The `.gitmodules` file failed to parse as an INI-style submodule table.
    ParseGitmodules(String),
    /// A git plumbing invocation failed with the captured stderr/stdout.
    GitInvocation {
        /// The argv summary used for the error context (e.g. `merge-base`).
        context: &'static str,
        /// The captured stderr from git, if any.
        stderr: String,
        /// The underlying `io::Error` from spawning or capturing the process.
        source: io::Error,
    },
    /// A git invocation returned a non-zero exit code without producing a
    /// usable result (e.g. unknown revision).
    GitExit {
        /// The argv summary used for the error context.
        context: &'static str,
        /// The exit code git returned.
        code: i32,
        /// Captured stderr, if any.
        stderr: String,
    },
    /// The supplied `--target-repo` value did not match any `.gitmodules` entry.
    UnknownTargetRepo(String),
}

impl Error {
    /// Constructs an [`Error::MissingGitmodules`].
    #[must_use]
    pub fn missing_gitmodules(source: io::Error) -> Self {
        Self::MissingGitmodules(source)
    }
    /// Constructs an [`Error::ParseGitmodules`].
    pub fn parse_gitmodules(detail: impl Into<String>) -> Self {
        Self::ParseGitmodules(detail.into())
    }
    /// Constructs an [`Error::GitInvocation`].
    pub fn git_invocation(
        context: &'static str,
        stderr: impl Into<String>,
        source: io::Error,
    ) -> Self {
        Self::GitInvocation {
            context,
            stderr: stderr.into(),
            source,
        }
    }
    /// Constructs an [`Error::GitExit`].
    pub fn git_exit(context: &'static str, code: i32, stderr: impl Into<String>) -> Self {
        Self::GitExit {
            context,
            code,
            stderr: stderr.into(),
        }
    }
    /// Constructs an [`Error::UnknownTargetRepo`].
    pub fn unknown_target_repo(name: impl Into<String>) -> Self {
        Self::UnknownTargetRepo(name.into())
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingGitmodules(source) => write!(
                f,
                "no readable `.gitmodules` at the supplied atlas-meta root: {source}"
            ),
            Self::ParseGitmodules(detail) => {
                write!(f, ".gitmodules parse failure: {detail}")
            }
            Self::GitInvocation {
                context,
                stderr,
                source,
            } => {
                let tail = if stderr.is_empty() {
                    String::new()
                } else {
                    format!(" stderr=`{stderr}`")
                };
                write!(f, "git `{context}` invocation failed{tail}: {source}")
            }
            Self::GitExit {
                context,
                code,
                stderr,
            } => {
                let tail = if stderr.is_empty() {
                    String::new()
                } else {
                    format!(" stderr=`{stderr}`")
                };
                write!(f, "git `{context}` exited {code}{tail}")
            }
            Self::UnknownTargetRepo(name) => {
                write!(
                    f,
                    "no `.gitmodules` submodule named `{name}` (use the bare name without the `repos/` prefix)"
                )
            }
        }
    }
}

impl StdError for Error {
    fn source(&self) -> Option<&(dyn StdError + 'static)> {
        match self {
            Self::MissingGitmodules(source) | Self::GitInvocation { source, .. } => Some(source),
            _ => None,
        }
    }
}

impl From<Error> for i32 {
    /// Maps an [`Error`] to the [`crate`] exit-code 2 (invocation error).
    fn from(_: Error) -> Self {
        2
    }
}

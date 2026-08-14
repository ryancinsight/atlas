use std::error::Error;
use std::fmt::{self, Display, Formatter};
use std::io;
use std::path::PathBuf;

/// Failure to discover or parse a Criterion comparison.
#[derive(Debug)]
#[non_exhaustive]
pub enum CheckError {
    /// The baseline is not a single safe path component.
    InvalidBaselineName(String),
    /// Criterion did not emit its expected output directory.
    MissingCriterionRoot(PathBuf),
    /// The named baseline does not occur below a Criterion root.
    MissingBaseline {
        /// Baseline name supplied by the caller.
        name: String,
        /// Criterion output directory that was searched.
        root: PathBuf,
    },
    /// The benchmark family cannot be represented by the confidence model.
    TooManyBenchmarks(usize),
    /// A filesystem operation failed.
    Io {
        /// Path involved in the failed operation.
        path: PathBuf,
        /// Underlying filesystem error.
        source: io::Error,
    },
    /// A Criterion estimate file was not valid JSON.
    Json {
        /// Invalid estimate file.
        path: PathBuf,
        /// Underlying JSON error.
        source: serde_json::Error,
    },
    /// A relative-change confidence interval violated Criterion invariants.
    InvalidEstimate {
        /// Invalid estimate file.
        path: PathBuf,
        /// Invariant violation.
        reason: &'static str,
    },
}

impl Display for CheckError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidBaselineName(name) => {
                write!(
                    formatter,
                    "baseline name must be one path component: {name:?}"
                )
            }
            Self::MissingCriterionRoot(path) => {
                write!(
                    formatter,
                    "Criterion output directory is missing: {}",
                    path.display()
                )
            }
            Self::MissingBaseline { name, root } => write!(
                formatter,
                "Criterion baseline {name:?} was not found below {}",
                root.display()
            ),
            Self::TooManyBenchmarks(count) => write!(
                formatter,
                "benchmark count {count} exceeds the supported u32 confidence domain"
            ),
            Self::Io { path, source } => {
                write!(formatter, "failed to read {}: {source}", path.display())
            }
            Self::Json { path, source } => {
                write!(
                    formatter,
                    "invalid Criterion JSON at {}: {source}",
                    path.display()
                )
            }
            Self::InvalidEstimate { path, reason } => write!(
                formatter,
                "invalid Criterion estimate at {}: {reason}",
                path.display()
            ),
        }
    }
}

impl Error for CheckError {
    // `Error::source` requires type erasure on this cold diagnostic path.
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Io { source, .. } => Some(source),
            Self::Json { source, .. } => Some(source),
            _ => None,
        }
    }
}

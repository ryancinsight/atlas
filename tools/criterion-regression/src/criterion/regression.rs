use std::error::Error;
use std::ffi::OsStr;
use std::fmt::{self, Display, Formatter};
use std::fs;
use std::io;
use std::path::{Component, Path, PathBuf};

use super::estimate::EstimateSet;

const ESTIMATES_FILE: &str = "estimates.json";

/// One benchmark whose relative median-change confidence interval is positive.
#[derive(Debug, PartialEq)]
#[must_use]
pub struct Regression {
    /// Benchmark identifier relative to `target/criterion`.
    pub benchmark: PathBuf,
    /// Criterion's relative median-change point estimate.
    pub point_estimate: f64,
    /// Lower bound of Criterion's relative median-change confidence interval.
    pub lower_bound: f64,
    /// Upper bound of Criterion's relative median-change confidence interval.
    pub upper_bound: f64,
    /// Confidence level used by Criterion.
    pub confidence_level: f64,
}

/// One baseline benchmark for which Criterion emitted no change estimate.
#[derive(Debug, PartialEq, Eq)]
#[must_use]
pub struct MissingComparison {
    /// Benchmark identifier relative to `target/criterion`.
    pub benchmark: PathBuf,
}

/// Complete result of auditing one Criterion base/head comparison.
#[derive(Debug, PartialEq)]
#[must_use]
pub struct Audit {
    /// Number of benchmark change estimates evaluated.
    pub comparisons: usize,
    /// Statistically significant median regressions.
    pub regressions: Vec<Regression>,
    /// Baseline benchmarks without a corresponding change estimate.
    pub missing_comparisons: Vec<MissingComparison>,
}

impl Audit {
    /// Returns `true` when the comparison cannot pass the regression gate.
    #[must_use]
    pub const fn has_failures(&self) -> bool {
        !self.regressions.is_empty() || !self.missing_comparisons.is_empty()
    }
}

/// Failure to discover or parse a Criterion comparison.
#[derive(Debug)]
#[non_exhaustive]
pub enum CheckError {
    /// The baseline is not a single safe path component.
    InvalidBaselineName(String),
    /// Criterion did not emit its expected output directory.
    MissingCriterionRoot(PathBuf),
    /// The named baseline does not occur below `target/criterion`.
    MissingBaseline {
        /// Baseline name supplied by the caller.
        name: String,
        /// Criterion output directory that was searched.
        root: PathBuf,
    },
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

/// Audits Criterion changes against a named saved baseline.
///
/// A regression is reported when Criterion's complete relative median-change
/// confidence interval is above zero. Missing comparisons fail closed so
/// deleted, renamed, or skipped benchmarks cannot silently reduce coverage.
///
/// # Errors
///
/// Returns [`CheckError`] when the baseline name is unsafe, Criterion output
/// is absent, filesystem traversal fails, or an estimate is malformed.
pub fn audit(workspace: &Path, baseline_name: &str) -> Result<Audit, CheckError> {
    validate_baseline_name(baseline_name)?;

    let criterion_root = workspace.join("target").join("criterion");
    if !criterion_root.is_dir() {
        return Err(CheckError::MissingCriterionRoot(criterion_root));
    }

    let mut benchmark_dirs = Vec::new();
    collect_baselines(
        &criterion_root,
        OsStr::new(baseline_name),
        &mut benchmark_dirs,
    )?;
    benchmark_dirs.sort_unstable();

    if benchmark_dirs.is_empty() {
        return Err(CheckError::MissingBaseline {
            name: baseline_name.to_owned(),
            root: criterion_root,
        });
    }

    let mut regressions = Vec::new();
    let mut missing_comparisons = Vec::new();
    let mut comparisons = 0;

    for benchmark_dir in benchmark_dirs {
        let benchmark = benchmark_dir
            .strip_prefix(&criterion_root)
            .map_or_else(|_| benchmark_dir.clone(), Path::to_path_buf);
        let change_path = benchmark_dir.join("change").join(ESTIMATES_FILE);

        if !change_path.is_file() {
            missing_comparisons.push(MissingComparison { benchmark });
            continue;
        }

        let estimate = read_estimate(&change_path)?;
        comparisons += 1;
        let interval = estimate.median.confidence_interval;

        if interval.lower_bound > 0.0 {
            regressions.push(Regression {
                benchmark,
                point_estimate: estimate.median.point_estimate,
                lower_bound: interval.lower_bound,
                upper_bound: interval.upper_bound,
                confidence_level: interval.confidence_level,
            });
        }
    }

    Ok(Audit {
        comparisons,
        regressions,
        missing_comparisons,
    })
}

fn validate_baseline_name(name: &str) -> Result<(), CheckError> {
    let mut components = Path::new(name).components();
    let is_one_normal_component =
        matches!(components.next(), Some(Component::Normal(_))) && components.next().is_none();

    if name.is_empty() || !is_one_normal_component {
        return Err(CheckError::InvalidBaselineName(name.to_owned()));
    }

    Ok(())
}

fn collect_baselines(
    directory: &Path,
    baseline_name: &OsStr,
    benchmark_dirs: &mut Vec<PathBuf>,
) -> Result<(), CheckError> {
    let entries = fs::read_dir(directory).map_err(|source| CheckError::Io {
        path: directory.to_path_buf(),
        source,
    })?;

    for entry in entries {
        let entry = entry.map_err(|source| CheckError::Io {
            path: directory.to_path_buf(),
            source,
        })?;
        let file_type = entry.file_type().map_err(|source| CheckError::Io {
            path: entry.path(),
            source,
        })?;

        if !file_type.is_dir() {
            continue;
        }

        if entry.file_name() == baseline_name && entry.path().join(ESTIMATES_FILE).is_file() {
            benchmark_dirs.push(directory.to_path_buf());
            continue;
        }

        collect_baselines(&entry.path(), baseline_name, benchmark_dirs)?;
    }

    Ok(())
}

fn read_estimate(path: &Path) -> Result<EstimateSet, CheckError> {
    let contents = fs::read(path).map_err(|source| CheckError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let estimate: EstimateSet =
        serde_json::from_slice(&contents).map_err(|source| CheckError::Json {
            path: path.to_path_buf(),
            source,
        })?;
    validate_estimate(path, &estimate)?;
    Ok(estimate)
}

fn validate_estimate(path: &Path, estimate: &EstimateSet) -> Result<(), CheckError> {
    let interval = &estimate.median.confidence_interval;
    let values = [
        estimate.median.point_estimate,
        interval.lower_bound,
        interval.upper_bound,
        interval.confidence_level,
    ];

    if !values.iter().all(|value| value.is_finite()) {
        return Err(CheckError::InvalidEstimate {
            path: path.to_path_buf(),
            reason: "median change contains a non-finite value",
        });
    }
    if !(0.0..1.0).contains(&interval.confidence_level) {
        return Err(CheckError::InvalidEstimate {
            path: path.to_path_buf(),
            reason: "confidence level must be between zero and one",
        });
    }
    if interval.lower_bound > interval.upper_bound {
        return Err(CheckError::InvalidEstimate {
            path: path.to_path_buf(),
            reason: "confidence interval bounds are reversed",
        });
    }

    Ok(())
}

use std::collections::{BTreeMap, BTreeSet};
use std::ffi::OsStr;
use std::fs;
use std::path::{Component, Path, PathBuf};

use super::error::CheckError;
use super::estimate::EstimateSet;
use super::model::RelativeMedianChange;

const ESTIMATES_FILE: &str = "estimates.json";

pub(super) struct ComparisonSet {
    pub(super) benchmarks: BTreeSet<PathBuf>,
    pub(super) changes: BTreeMap<PathBuf, RelativeMedianChange>,
}

pub(super) fn discover(
    criterion_root: &Path,
    baseline_name: &str,
) -> Result<ComparisonSet, CheckError> {
    validate_baseline_name(baseline_name)?;
    if !criterion_root.is_dir() {
        return Err(CheckError::MissingCriterionRoot(
            criterion_root.to_path_buf(),
        ));
    }

    let mut benchmark_dirs = Vec::new();
    collect_baselines(
        criterion_root,
        OsStr::new(baseline_name),
        &mut benchmark_dirs,
    )?;
    benchmark_dirs.sort_unstable();

    if benchmark_dirs.is_empty() {
        return Err(CheckError::MissingBaseline {
            name: baseline_name.to_owned(),
            root: criterion_root.to_path_buf(),
        });
    }

    let mut benchmarks = BTreeSet::new();
    let mut changes = BTreeMap::new();
    for benchmark_dir in benchmark_dirs {
        let benchmark = benchmark_dir
            .strip_prefix(criterion_root)
            .map_or_else(|_| benchmark_dir.clone(), Path::to_path_buf);
        benchmarks.insert(benchmark.clone());

        let change_path = benchmark_dir.join("change").join(ESTIMATES_FILE);
        if change_path.is_file() {
            changes.insert(benchmark, read_estimate(&change_path)?);
        }
    }

    Ok(ComparisonSet {
        benchmarks,
        changes,
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

fn read_estimate(path: &Path) -> Result<RelativeMedianChange, CheckError> {
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

    let interval = estimate.median.confidence_interval;
    Ok(RelativeMedianChange {
        point_estimate: estimate.median.point_estimate,
        lower_bound: interval.lower_bound,
        upper_bound: interval.upper_bound,
        confidence_level: interval.confidence_level,
    })
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

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use super::discovery::{ComparisonSet, discover};
use super::error::CheckError;
use super::model::{
    Audit, InsufficientConfidence, MeasurementOrder, MissingComparison, Regression,
    UniverseMismatch,
};

const FAMILY_WISE_ERROR_RATE: f64 = 0.05;

/// Returns the per-comparison confidence level required for a benchmark family.
///
/// Bonferroni's inequality bounds the probability of any false regression by
/// `m * alpha` for `m` benchmarks without assuming independence. A
/// counterbalanced regression is a subset of a confidence-interval miss in
/// either fixed order, so `alpha = 0.05 / m` controls family-wise error at 5%.
/// This is the simultaneous-interval construction specified by the
/// [NIST/SEMATECH handbook](https://www.itl.nist.gov/div898/handbook/prc/section4/prc463.htm).
///
/// # Examples
///
/// ```no_run
/// use std::path::Path;
/// use atlas_criterion_gate::criterion::required_confidence_level;
///
/// let confidence = required_confidence_level(
///     Path::new("target/criterion"),
///     "atlas-base",
/// )?;
/// println!("{confidence:.17}");
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
///
/// # Errors
///
/// Returns [`CheckError`] when the Criterion root or named baseline is absent.
pub fn required_confidence_level(
    criterion_root: &Path,
    baseline_name: &str,
) -> Result<f64, CheckError> {
    let comparisons = discover(criterion_root, baseline_name)?;
    confidence_for_count(comparisons.benchmarks.len())
}

pub(super) struct CounterbalancedAudit {
    pub(super) audit: Audit,
    pub(super) benchmarks: BTreeSet<PathBuf>,
}

pub(super) fn audit_counterbalanced(
    baseline_first_root: &Path,
    candidate_first_root: &Path,
    baseline_name: &str,
) -> Result<CounterbalancedAudit, CheckError> {
    let baseline_first = discover(baseline_first_root, baseline_name)?;
    let candidate_first = discover(candidate_first_root, baseline_name)?;
    classify(&baseline_first, &candidate_first)
}

fn classify(
    baseline_first: &ComparisonSet,
    candidate_first: &ComparisonSet,
) -> Result<CounterbalancedAudit, CheckError> {
    let benchmarks: BTreeSet<_> = baseline_first
        .benchmarks
        .union(&candidate_first.benchmarks)
        .cloned()
        .collect();
    let required_confidence_level = confidence_for_count(benchmarks.len())?;

    let universe_mismatches = baseline_first
        .benchmarks
        .symmetric_difference(&candidate_first.benchmarks)
        .map(|benchmark| UniverseMismatch {
            benchmark: benchmark.clone(),
            present_in: if baseline_first.benchmarks.contains(benchmark) {
                MeasurementOrder::BaselineFirst
            } else {
                MeasurementOrder::CandidateFirst
            },
        })
        .collect();

    let mut missing_comparisons = Vec::new();
    let mut insufficient_confidence = Vec::new();
    let mut regressions = Vec::new();
    let mut comparisons = 0;

    for benchmark in baseline_first
        .benchmarks
        .intersection(&candidate_first.benchmarks)
    {
        let forward = baseline_first.changes.get(benchmark);
        let reverse = candidate_first.changes.get(benchmark);

        record_missing(
            &mut missing_comparisons,
            benchmark,
            MeasurementOrder::BaselineFirst,
            forward.is_none(),
        );
        record_missing(
            &mut missing_comparisons,
            benchmark,
            MeasurementOrder::CandidateFirst,
            reverse.is_none(),
        );

        let (Some(forward), Some(reverse)) = (forward, reverse) else {
            continue;
        };
        comparisons += 1;

        record_confidence(
            &mut insufficient_confidence,
            benchmark,
            MeasurementOrder::BaselineFirst,
            forward.confidence_level,
            required_confidence_level,
        );
        record_confidence(
            &mut insufficient_confidence,
            benchmark,
            MeasurementOrder::CandidateFirst,
            reverse.confidence_level,
            required_confidence_level,
        );

        if forward.confidence_level >= required_confidence_level
            && reverse.confidence_level >= required_confidence_level
            && forward.lower_bound > 0.0
            && reverse.upper_bound < 0.0
        {
            regressions.push(Regression {
                benchmark: benchmark.clone(),
                baseline_first: *forward,
                candidate_first: *reverse,
            });
        }
    }

    Ok(CounterbalancedAudit {
        audit: Audit {
            comparisons,
            required_confidence_level,
            regressions,
            missing_comparisons,
            universe_mismatches,
            insufficient_confidence,
        },
        benchmarks,
    })
}

fn confidence_for_count(benchmark_count: usize) -> Result<f64, CheckError> {
    let count = u32::try_from(benchmark_count.max(1))
        .map_err(|_| CheckError::TooManyBenchmarks(benchmark_count))?;
    Ok(1.0 - FAMILY_WISE_ERROR_RATE / f64::from(count))
}

fn record_missing(
    missing: &mut Vec<MissingComparison>,
    benchmark: &Path,
    order: MeasurementOrder,
    is_missing: bool,
) {
    if is_missing {
        missing.push(MissingComparison {
            benchmark: benchmark.to_path_buf(),
            order,
        });
    }
}

fn record_confidence(
    insufficient: &mut Vec<InsufficientConfidence>,
    benchmark: &Path,
    order: MeasurementOrder,
    observed: f64,
    required: f64,
) {
    if observed < required {
        insufficient.push(InsufficientConfidence {
            benchmark: benchmark.to_path_buf(),
            order,
            observed,
            required,
        });
    }
}

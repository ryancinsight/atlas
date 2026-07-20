use std::collections::BTreeMap;
use std::path::Path;

use super::counterbalanced::audit_counterbalanced;
use super::error::CheckError;
use super::model::{
    ReplicatedAudit, ReplicatedRegression, Replication, ReplicationUniverseMismatch,
};

/// Audits two phase-reversed, counterbalanced Criterion replications.
///
/// The first replication occupies run positions as
/// baseline-candidate-candidate-baseline (ABBA). The second reverses the
/// phases to candidate-baseline-baseline-candidate (BAAB). Across all eight
/// positions, each revision has equal position and squared-position sums, so
/// their complete-schedule exposure is balanced for constant, linear, and
/// quadratic period terms.
///
/// A regression requires opposite-order agreement inside each replication and
/// agreement across both replications. Benchmark-universe differences,
/// missing estimates, and intervals below the family-wise confidence
/// requirement fail closed.
///
/// # Examples
///
/// ```no_run
/// use std::path::Path;
/// use atlas_criterion_gate::criterion::audit_replicated_counterbalanced;
///
/// let audit = audit_replicated_counterbalanced(
///     Path::new("target/criterion-first-baseline-first"),
///     Path::new("target/criterion-first-candidate-first"),
///     Path::new("target/criterion-second-baseline-first"),
///     Path::new("target/criterion-second-candidate-first"),
///     "atlas-base",
/// )?;
/// assert!(!audit.has_failures());
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
///
/// # Errors
///
/// Returns [`CheckError`] when any Criterion root or named baseline is absent,
/// filesystem traversal fails, or an estimate is malformed.
pub fn audit_replicated_counterbalanced(
    first_baseline_first_root: &Path,
    first_candidate_first_root: &Path,
    second_baseline_first_root: &Path,
    second_candidate_first_root: &Path,
    baseline_name: &str,
) -> Result<ReplicatedAudit, CheckError> {
    let first = audit_counterbalanced(
        first_baseline_first_root,
        first_candidate_first_root,
        baseline_name,
    )?;
    let second = audit_counterbalanced(
        second_baseline_first_root,
        second_candidate_first_root,
        baseline_name,
    )?;

    let replication_universe_mismatches = first
        .benchmarks
        .symmetric_difference(&second.benchmarks)
        .map(|benchmark| ReplicationUniverseMismatch {
            benchmark: benchmark.clone(),
            present_in: if first.benchmarks.contains(benchmark) {
                Replication::First
            } else {
                Replication::Second
            },
        })
        .collect();

    let second_regressions: BTreeMap<_, _> = second
        .audit
        .regressions
        .iter()
        .map(|regression| (regression.benchmark.as_path(), regression))
        .collect();
    let regressions = first
        .audit
        .regressions
        .iter()
        .filter_map(|first_regression| {
            second_regressions
                .get(first_regression.benchmark.as_path())
                .map(|second_regression| ReplicatedRegression {
                    benchmark: first_regression.benchmark.clone(),
                    first: first_regression.clone(),
                    second: (*second_regression).clone(),
                })
        })
        .collect();

    Ok(ReplicatedAudit {
        first: first.audit,
        second: second.audit,
        regressions,
        replication_universe_mismatches,
    })
}

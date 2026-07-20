use std::path::PathBuf;

/// Execution order for one half of a counterbalanced comparison.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MeasurementOrder {
    /// The baseline revision ran before the candidate revision.
    BaselineFirst,
    /// The candidate revision ran before the baseline revision.
    CandidateFirst,
}

/// Criterion's relative median-change estimate for one execution order.
#[derive(Clone, Copy, Debug, PartialEq)]
#[must_use]
pub struct RelativeMedianChange {
    /// Relative median-change point estimate.
    pub point_estimate: f64,
    /// Lower confidence-interval bound.
    pub lower_bound: f64,
    /// Upper confidence-interval bound.
    pub upper_bound: f64,
    /// Confidence level used by Criterion.
    pub confidence_level: f64,
}

/// A candidate slowdown reproduced in both execution orders.
#[derive(Debug, PartialEq)]
#[must_use]
pub struct Regression {
    /// Benchmark identifier relative to the Criterion root.
    pub benchmark: PathBuf,
    /// Candidate-versus-baseline estimate from baseline-first execution.
    pub baseline_first: RelativeMedianChange,
    /// Baseline-versus-candidate estimate from candidate-first execution.
    pub candidate_first: RelativeMedianChange,
}

/// A baseline benchmark for which Criterion emitted no change estimate.
#[derive(Debug, PartialEq, Eq)]
#[must_use]
pub struct MissingComparison {
    /// Benchmark identifier relative to the Criterion root.
    pub benchmark: PathBuf,
    /// Execution order whose change estimate is absent.
    pub order: MeasurementOrder,
}

/// A benchmark present in only one execution order.
#[derive(Debug, PartialEq, Eq)]
#[must_use]
pub struct UniverseMismatch {
    /// Benchmark identifier relative to the Criterion root.
    pub benchmark: PathBuf,
    /// Execution order in which the benchmark is present.
    pub present_in: MeasurementOrder,
}

/// A comparison whose interval does not control family-wise error.
#[derive(Debug, PartialEq)]
#[must_use]
pub struct InsufficientConfidence {
    /// Benchmark identifier relative to the Criterion root.
    pub benchmark: PathBuf,
    /// Execution order whose confidence level is insufficient.
    pub order: MeasurementOrder,
    /// Confidence level recorded by Criterion.
    pub observed: f64,
    /// Minimum confidence level required for the benchmark universe.
    pub required: f64,
}

/// Complete counterbalanced Criterion audit.
#[derive(Debug, PartialEq)]
#[must_use]
pub struct Audit {
    /// Number of benchmarks with change estimates in both execution orders.
    pub comparisons: usize,
    /// Minimum per-comparison confidence level for family-wise control.
    pub required_confidence_level: f64,
    /// Candidate slowdowns reproduced in both execution orders.
    pub regressions: Vec<Regression>,
    /// Baseline entries without corresponding change estimates.
    pub missing_comparisons: Vec<MissingComparison>,
    /// Benchmarks absent from one execution order.
    pub universe_mismatches: Vec<UniverseMismatch>,
    /// Change estimates below the required confidence level.
    pub insufficient_confidence: Vec<InsufficientConfidence>,
}

impl Audit {
    /// Returns `true` when the counterbalanced comparison cannot pass.
    #[must_use]
    pub const fn has_failures(&self) -> bool {
        !self.regressions.is_empty()
            || !self.missing_comparisons.is_empty()
            || !self.universe_mismatches.is_empty()
            || !self.insufficient_confidence.is_empty()
    }
}

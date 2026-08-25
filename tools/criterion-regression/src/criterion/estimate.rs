use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub(super) struct EstimateSet {
    pub(super) median: Estimate,
}

#[derive(Debug, Deserialize)]
pub(super) struct Estimate {
    pub(super) confidence_interval: ConfidenceInterval,
    pub(super) point_estimate: f64,
}

#[derive(Debug, Deserialize)]
pub(super) struct ConfidenceInterval {
    pub(super) confidence_level: f64,
    pub(super) lower_bound: f64,
    pub(super) upper_bound: f64,
}

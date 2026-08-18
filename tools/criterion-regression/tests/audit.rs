//! Value-semantic tests for phase-replicated Criterion classification.

#![allow(clippy::unwrap_used)]

use std::fs;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};

use atlas_criterion_gate::criterion::{
    CheckError, MeasurementOrder, ReplicatedAudit, Replication, audit_replicated_counterbalanced,
    required_confidence_level,
};

static FIXTURE_ID: AtomicU64 = AtomicU64::new(0);

struct Fixture {
    root: PathBuf,
}

impl Fixture {
    fn new() -> Self {
        let id = FIXTURE_ID.fetch_add(1, Ordering::Relaxed);
        let root =
            std::env::temp_dir().join(format!("atlas-criterion-gate-{}-{id}", std::process::id()));
        fs::create_dir_all(&root).unwrap();
        Self { root }
    }

    fn criterion_root(&self, replication: Replication, order: MeasurementOrder) -> PathBuf {
        let replication = match replication {
            Replication::First => "first",
            Replication::Second => "second",
        };
        let order = match order {
            MeasurementOrder::BaselineFirst => "baseline-first",
            MeasurementOrder::CandidateFirst => "candidate-first",
        };
        self.root.join(replication).join(order)
    }

    fn benchmark(
        &self,
        replication: Replication,
        order: MeasurementOrder,
        name: &str,
        baseline: &str,
        change: Option<&str>,
    ) {
        let root = self.criterion_root(replication, order).join(name);
        fs::create_dir_all(root.join(baseline)).unwrap();
        fs::write(root.join(baseline).join("estimates.json"), "{}").unwrap();
        if let Some(change) = change {
            fs::create_dir_all(root.join("change")).unwrap();
            fs::write(root.join("change").join("estimates.json"), change).unwrap();
        }
    }

    fn comparison(&self, replication: Replication, name: &str, forward: &str, reverse: &str) {
        self.benchmark(
            replication,
            MeasurementOrder::BaselineFirst,
            name,
            "atlas-base",
            Some(forward),
        );
        self.benchmark(
            replication,
            MeasurementOrder::CandidateFirst,
            name,
            "atlas-base",
            Some(reverse),
        );
    }

    fn audit(&self) -> Result<ReplicatedAudit, CheckError> {
        audit_replicated_counterbalanced(
            &self.criterion_root(Replication::First, MeasurementOrder::BaselineFirst),
            &self.criterion_root(Replication::First, MeasurementOrder::CandidateFirst),
            &self.criterion_root(Replication::Second, MeasurementOrder::BaselineFirst),
            &self.criterion_root(Replication::Second, MeasurementOrder::CandidateFirst),
            "atlas-base",
        )
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        if let Err(error) = fs::remove_dir_all(&self.root) {
            assert!(
                std::thread::panicking(),
                "failed to remove fixture {}: {error}",
                self.root.display()
            );
        }
    }
}

fn estimate(point: f64, lower: f64, upper: f64, confidence: f64) -> String {
    format!(
        r#"{{
            "median": {{
                "confidence_interval": {{
                    "confidence_level": {confidence},
                    "lower_bound": {lower},
                    "upper_bound": {upper}
                }},
                "point_estimate": {point},
                "standard_error": 0.01
            }}
        }}"#
    )
}

fn regression_estimates(confidence: f64) -> (String, String) {
    (
        estimate(0.12, 0.04, 0.20, confidence),
        estimate(-0.11, -0.18, -0.03, confidence),
    )
}

fn stable_estimates(confidence: f64) -> (String, String) {
    (
        estimate(0.01, -0.04, 0.06, confidence),
        estimate(-0.01, -0.06, 0.04, confidence),
    )
}

#[test]
fn detects_nested_regression_in_both_replications() {
    let fixture = Fixture::new();
    let (forward, reverse) = regression_estimates(0.95);
    for replication in [Replication::First, Replication::Second] {
        fixture.comparison(replication, "group/operation/4096", &forward, &reverse);
    }

    let result = fixture.audit().unwrap();

    assert_eq!(result.first.comparisons, 1);
    assert_eq!(result.second.comparisons, 1);
    assert_eq!(result.regressions.len(), 1);
    assert_eq!(
        result.regressions[0].benchmark,
        PathBuf::from("group/operation/4096")
    );
    assert_eq!(
        result.regressions[0]
            .first
            .baseline_first
            .point_estimate
            .to_bits(),
        0.12_f64.to_bits()
    );
    assert_eq!(
        result.regressions[0]
            .second
            .candidate_first
            .point_estimate
            .to_bits(),
        (-0.11_f64).to_bits()
    );
    assert!(result.has_failures());
}

#[test]
fn rejects_slowdown_confined_to_one_execution_order() {
    let fixture = Fixture::new();
    let (regression_forward, regression_reverse) = regression_estimates(0.95);
    let (stable_forward, stable_reverse) = stable_estimates(0.95);
    fixture.comparison(
        Replication::First,
        "group/operation",
        &regression_forward,
        &regression_reverse,
    );
    fixture.comparison(
        Replication::Second,
        "group/operation",
        &stable_forward,
        &stable_reverse,
    );

    let result = fixture.audit().unwrap();

    assert_eq!(result.first.regressions.len(), 1);
    assert!(result.second.regressions.is_empty());
    assert!(result.regressions.is_empty());
    assert!(!result.has_failures());
}

#[test]
fn fails_closed_when_second_replication_has_no_change_estimate() {
    let fixture = Fixture::new();
    let (stable_forward, stable_reverse) = stable_estimates(0.95);
    fixture.comparison(
        Replication::First,
        "group/missing",
        &stable_forward,
        &stable_reverse,
    );
    fixture.benchmark(
        Replication::Second,
        MeasurementOrder::BaselineFirst,
        "group/missing",
        "atlas-base",
        None,
    );
    fixture.benchmark(
        Replication::Second,
        MeasurementOrder::CandidateFirst,
        "group/missing",
        "atlas-base",
        Some(&stable_reverse),
    );

    let result = fixture.audit().unwrap();

    assert_eq!(result.second.comparisons, 0);
    assert_eq!(result.second.missing_comparisons.len(), 1);
    assert_eq!(
        result.second.missing_comparisons[0].order,
        MeasurementOrder::BaselineFirst
    );
    assert!(result.has_failures());
}

#[test]
fn fails_closed_on_within_replication_universe_mismatch() {
    let fixture = Fixture::new();
    let (stable_forward, stable_reverse) = stable_estimates(0.975);
    fixture.benchmark(
        Replication::First,
        MeasurementOrder::BaselineFirst,
        "group/base-only",
        "atlas-base",
        Some(&stable_forward),
    );
    fixture.benchmark(
        Replication::First,
        MeasurementOrder::CandidateFirst,
        "group/candidate-only",
        "atlas-base",
        Some(&stable_reverse),
    );
    for name in ["group/base-only", "group/candidate-only"] {
        fixture.comparison(Replication::Second, name, &stable_forward, &stable_reverse);
    }

    let result = fixture.audit().unwrap();

    assert_eq!(result.first.universe_mismatches.len(), 2);
    assert!(result.has_failures());
}

#[test]
fn fails_closed_on_replication_universe_mismatch() {
    let fixture = Fixture::new();
    let (stable_forward, stable_reverse) = stable_estimates(0.95);
    fixture.comparison(
        Replication::First,
        "group/first-only",
        &stable_forward,
        &stable_reverse,
    );
    fixture.comparison(
        Replication::Second,
        "group/second-only",
        &stable_forward,
        &stable_reverse,
    );

    let result = fixture.audit().unwrap();

    assert_eq!(result.replication_universe_mismatches.len(), 2);
    assert_eq!(
        result.replication_universe_mismatches[0].present_in,
        Replication::First
    );
    assert_eq!(
        result.replication_universe_mismatches[1].present_in,
        Replication::Second
    );
    assert!(result.has_failures());
}

#[test]
fn fails_closed_below_familywise_confidence() {
    let fixture = Fixture::new();
    let (forward, reverse) = regression_estimates(0.95);
    for replication in [Replication::First, Replication::Second] {
        for name in ["first", "second"] {
            fixture.comparison(replication, name, &forward, &reverse);
        }
    }

    let result = fixture.audit().unwrap();

    assert_eq!(
        result.first.required_confidence_level.to_bits(),
        (1.0_f64 - 0.05 / 2.0).to_bits()
    );
    assert_eq!(result.first.insufficient_confidence.len(), 4);
    assert_eq!(result.second.insufficient_confidence.len(), 4);
    assert!(result.regressions.is_empty());
    assert!(result.has_failures());
}

#[test]
fn computes_bonferroni_confidence_from_baseline_count() {
    let fixture = Fixture::new();
    for name in ["one", "two", "three", "four"] {
        fixture.benchmark(
            Replication::First,
            MeasurementOrder::BaselineFirst,
            name,
            "atlas-base",
            None,
        );
    }

    let confidence = required_confidence_level(
        &fixture.criterion_root(Replication::First, MeasurementOrder::BaselineFirst),
        "atlas-base",
    )
    .unwrap();

    assert_eq!(confidence.to_bits(), (1.0_f64 - 0.05 / 4.0).to_bits());
}

#[test]
fn rejects_path_traversal_baseline_name() {
    let fixture = Fixture::new();

    let error = required_confidence_level(
        &fixture.criterion_root(Replication::First, MeasurementOrder::BaselineFirst),
        "../base",
    )
    .unwrap_err();

    assert!(matches!(error, CheckError::InvalidBaselineName(_)));
}

#[test]
fn reports_absent_named_baseline() {
    let fixture = Fixture::new();
    let root = fixture.criterion_root(Replication::First, MeasurementOrder::BaselineFirst);
    fs::create_dir_all(&root).unwrap();

    let error = required_confidence_level(&root, "atlas-base").unwrap_err();

    assert!(matches!(error, CheckError::MissingBaseline { .. }));
}

#[test]
fn rejects_malformed_change_estimate_in_second_replication() {
    let fixture = Fixture::new();
    let (stable_forward, stable_reverse) = stable_estimates(0.95);
    fixture.comparison(
        Replication::First,
        "group/malformed",
        &stable_forward,
        &stable_reverse,
    );
    fixture.comparison(
        Replication::Second,
        "group/malformed",
        "{not-json",
        &stable_reverse,
    );

    let error = fixture.audit().unwrap_err();

    assert!(matches!(error, CheckError::Json { .. }));
}

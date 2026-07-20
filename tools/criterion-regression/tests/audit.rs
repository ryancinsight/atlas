//! Value-semantic tests for counterbalanced Criterion classification.

#![allow(clippy::unwrap_used)]

use std::fs;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};

use atlas_criterion_gate::criterion::{
    CheckError, MeasurementOrder, audit_counterbalanced, required_confidence_level,
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

    fn criterion_root(&self, order: MeasurementOrder) -> PathBuf {
        self.root.join(match order {
            MeasurementOrder::BaselineFirst => "baseline-first",
            MeasurementOrder::CandidateFirst => "candidate-first",
        })
    }

    fn benchmark(&self, order: MeasurementOrder, name: &str, baseline: &str, change: Option<&str>) {
        let root = self.criterion_root(order).join(name);
        fs::create_dir_all(root.join(baseline)).unwrap();
        fs::write(root.join(baseline).join("estimates.json"), "{}").unwrap();
        if let Some(change) = change {
            fs::create_dir_all(root.join("change")).unwrap();
            fs::write(root.join("change").join("estimates.json"), change).unwrap();
        }
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.root).unwrap();
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

fn audit(fixture: &Fixture) -> atlas_criterion_gate::criterion::Audit {
    audit_counterbalanced(
        &fixture.criterion_root(MeasurementOrder::BaselineFirst),
        &fixture.criterion_root(MeasurementOrder::CandidateFirst),
        "atlas-base",
    )
    .unwrap()
}

#[test]
fn detects_nested_counterbalanced_regression() {
    let fixture = Fixture::new();
    fixture.benchmark(
        MeasurementOrder::BaselineFirst,
        "group/operation/4096",
        "atlas-base",
        Some(&estimate(0.12, 0.04, 0.20, 0.95)),
    );
    fixture.benchmark(
        MeasurementOrder::CandidateFirst,
        "group/operation/4096",
        "atlas-base",
        Some(&estimate(-0.11, -0.18, -0.03, 0.95)),
    );

    let result = audit(&fixture);

    assert_eq!(result.comparisons, 1);
    assert_eq!(result.regressions.len(), 1);
    assert_eq!(
        result.regressions[0].benchmark,
        PathBuf::from("group/operation/4096")
    );
    assert_eq!(
        result.regressions[0]
            .baseline_first
            .point_estimate
            .to_bits(),
        0.12_f64.to_bits()
    );
    assert_eq!(
        result.regressions[0]
            .candidate_first
            .point_estimate
            .to_bits(),
        (-0.11_f64).to_bits()
    );
    assert!(result.has_failures());
}

#[test]
fn accepts_order_sensitive_slowdown() {
    let fixture = Fixture::new();
    fixture.benchmark(
        MeasurementOrder::BaselineFirst,
        "group/operation",
        "atlas-base",
        Some(&estimate(0.12, 0.04, 0.20, 0.95)),
    );
    fixture.benchmark(
        MeasurementOrder::CandidateFirst,
        "group/operation",
        "atlas-base",
        Some(&estimate(0.02, -0.03, 0.07, 0.95)),
    );

    let result = audit(&fixture);

    assert_eq!(result.comparisons, 1);
    assert!(result.regressions.is_empty());
    assert!(result.missing_comparisons.is_empty());
    assert!(!result.has_failures());
}

#[test]
fn fails_closed_when_either_order_has_no_change_estimate() {
    let fixture = Fixture::new();
    fixture.benchmark(
        MeasurementOrder::BaselineFirst,
        "group/missing-forward",
        "atlas-base",
        None,
    );
    fixture.benchmark(
        MeasurementOrder::CandidateFirst,
        "group/missing-forward",
        "atlas-base",
        Some(&estimate(-0.11, -0.18, -0.03, 0.95)),
    );
    fixture.benchmark(
        MeasurementOrder::BaselineFirst,
        "group/missing-reverse",
        "atlas-base",
        Some(&estimate(0.12, 0.04, 0.20, 0.95)),
    );
    fixture.benchmark(
        MeasurementOrder::CandidateFirst,
        "group/missing-reverse",
        "atlas-base",
        None,
    );

    let result = audit(&fixture);

    assert_eq!(result.comparisons, 0);
    assert_eq!(result.missing_comparisons.len(), 2);
    assert_eq!(
        result.missing_comparisons[0].benchmark,
        PathBuf::from("group/missing-forward")
    );
    assert_eq!(
        result.missing_comparisons[0].order,
        MeasurementOrder::BaselineFirst
    );
    assert_eq!(
        result.missing_comparisons[1].benchmark,
        PathBuf::from("group/missing-reverse")
    );
    assert_eq!(
        result.missing_comparisons[1].order,
        MeasurementOrder::CandidateFirst
    );
    assert!(result.has_failures());
}

#[test]
fn fails_closed_on_benchmark_universe_mismatch() {
    let fixture = Fixture::new();
    fixture.benchmark(
        MeasurementOrder::BaselineFirst,
        "group/base-only",
        "atlas-base",
        Some(&estimate(0.0, -0.1, 0.1, 0.975)),
    );
    fixture.benchmark(
        MeasurementOrder::CandidateFirst,
        "group/candidate-only",
        "atlas-base",
        Some(&estimate(0.0, -0.1, 0.1, 0.975)),
    );

    let result = audit(&fixture);

    assert_eq!(result.universe_mismatches.len(), 2);
    assert!(result.has_failures());
}

#[test]
fn fails_closed_below_familywise_confidence() {
    let fixture = Fixture::new();
    for name in ["first", "second"] {
        fixture.benchmark(
            MeasurementOrder::BaselineFirst,
            name,
            "atlas-base",
            Some(&estimate(0.12, 0.04, 0.20, 0.95)),
        );
        fixture.benchmark(
            MeasurementOrder::CandidateFirst,
            name,
            "atlas-base",
            Some(&estimate(-0.11, -0.18, -0.03, 0.95)),
        );
    }

    let result = audit(&fixture);

    assert_eq!(
        result.required_confidence_level.to_bits(),
        (1.0_f64 - 0.05 / 2.0).to_bits()
    );
    assert_eq!(result.insufficient_confidence.len(), 4);
    assert!(result.regressions.is_empty());
    assert!(result.has_failures());
}

#[test]
fn computes_bonferroni_confidence_from_baseline_count() {
    let fixture = Fixture::new();
    for name in ["one", "two", "three", "four"] {
        fixture.benchmark(MeasurementOrder::BaselineFirst, name, "atlas-base", None);
    }

    let confidence = required_confidence_level(
        &fixture.criterion_root(MeasurementOrder::BaselineFirst),
        "atlas-base",
    )
    .unwrap();

    assert_eq!(confidence.to_bits(), (1.0_f64 - 0.05 / 4.0).to_bits());
}

#[test]
fn rejects_path_traversal_baseline_name() {
    let fixture = Fixture::new();

    let error = required_confidence_level(
        &fixture.criterion_root(MeasurementOrder::BaselineFirst),
        "../base",
    )
    .unwrap_err();

    assert!(matches!(error, CheckError::InvalidBaselineName(_)));
}

#[test]
fn reports_absent_named_baseline() {
    let fixture = Fixture::new();
    let root = fixture.criterion_root(MeasurementOrder::BaselineFirst);
    fs::create_dir_all(&root).unwrap();

    let error = required_confidence_level(&root, "atlas-base").unwrap_err();

    assert!(matches!(error, CheckError::MissingBaseline { .. }));
}

#[test]
fn rejects_malformed_change_estimate() {
    let fixture = Fixture::new();
    fixture.benchmark(
        MeasurementOrder::BaselineFirst,
        "group/malformed",
        "atlas-base",
        Some("{not-json"),
    );
    fixture.benchmark(
        MeasurementOrder::CandidateFirst,
        "group/malformed",
        "atlas-base",
        Some(&estimate(0.0, -0.1, 0.1, 0.95)),
    );

    let error = audit_counterbalanced(
        &fixture.criterion_root(MeasurementOrder::BaselineFirst),
        &fixture.criterion_root(MeasurementOrder::CandidateFirst),
        "atlas-base",
    )
    .unwrap_err();

    assert!(matches!(error, CheckError::Json { .. }));
}

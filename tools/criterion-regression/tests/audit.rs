//! Value-semantic tests for Criterion comparison discovery and classification.

#![allow(clippy::unwrap_used)]

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use atlas_criterion_gate::criterion::{CheckError, audit};

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

    fn workspace(&self) -> &Path {
        &self.root
    }

    fn benchmark(&self, name: &str, baseline: &str, change: Option<&str>) {
        let root = self.root.join("target").join("criterion").join(name);
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

fn estimate(point: f64, lower: f64, upper: f64) -> String {
    format!(
        r#"{{
            "median": {{
                "confidence_interval": {{
                    "confidence_level": 0.95,
                    "lower_bound": {lower},
                    "upper_bound": {upper}
                }},
                "point_estimate": {point},
                "standard_error": 0.01
            }}
        }}"#
    )
}

#[test]
fn detects_nested_statistically_significant_regression() {
    let fixture = Fixture::new();
    fixture.benchmark(
        "group/operation/4096",
        "atlas-base",
        Some(&estimate(0.12, 0.04, 0.20)),
    );

    let result = audit(fixture.workspace(), "atlas-base").unwrap();

    assert_eq!(result.comparisons, 1);
    assert_eq!(result.regressions.len(), 1);
    assert_eq!(
        result.regressions[0].benchmark,
        PathBuf::from("group/operation/4096")
    );
    assert!(result.has_failures());
}

#[test]
fn accepts_confidence_interval_overlapping_zero() {
    let fixture = Fixture::new();
    fixture.benchmark(
        "group/operation",
        "atlas-base",
        Some(&estimate(0.02, -0.03, 0.07)),
    );

    let result = audit(fixture.workspace(), "atlas-base").unwrap();

    assert_eq!(result.comparisons, 1);
    assert!(result.regressions.is_empty());
    assert!(result.missing_comparisons.is_empty());
    assert!(!result.has_failures());
}

#[test]
fn fails_closed_when_baseline_has_no_change_estimate() {
    let fixture = Fixture::new();
    fixture.benchmark("group/removed", "atlas-base", None);

    let result = audit(fixture.workspace(), "atlas-base").unwrap();

    assert_eq!(result.comparisons, 0);
    assert_eq!(result.missing_comparisons.len(), 1);
    assert_eq!(
        result.missing_comparisons[0].benchmark,
        PathBuf::from("group/removed")
    );
    assert!(result.has_failures());
}

#[test]
fn rejects_path_traversal_baseline_name() {
    let fixture = Fixture::new();

    let error = audit(fixture.workspace(), "../base").unwrap_err();

    assert!(matches!(error, CheckError::InvalidBaselineName(_)));
}

#[test]
fn reports_absent_named_baseline() {
    let fixture = Fixture::new();
    fs::create_dir_all(fixture.workspace().join("target").join("criterion")).unwrap();

    let error = audit(fixture.workspace(), "atlas-base").unwrap_err();

    assert!(matches!(error, CheckError::MissingBaseline { .. }));
}

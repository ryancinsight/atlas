//! Criterion result discovery and regression classification.

mod counterbalanced;
mod discovery;
mod error;
mod estimate;
mod model;

pub use counterbalanced::{audit_counterbalanced, required_confidence_level};
pub use error::CheckError;
pub use model::{
    Audit, InsufficientConfidence, MeasurementOrder, MissingComparison, Regression,
    RelativeMedianChange, UniverseMismatch,
};

//! Criterion result discovery and regression classification.

mod counterbalanced;
mod discovery;
mod error;
mod estimate;
mod model;
mod replicated;

pub use counterbalanced::required_confidence_level;
pub use error::CheckError;
pub use model::{
    Audit, InsufficientConfidence, MeasurementOrder, MissingComparison, Regression,
    RelativeMedianChange, ReplicatedAudit, ReplicatedRegression, Replication,
    ReplicationUniverseMismatch, UniverseMismatch,
};
pub use replicated::audit_replicated_counterbalanced;

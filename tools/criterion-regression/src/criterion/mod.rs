//! Criterion result discovery and regression classification.

mod estimate;
mod regression;

pub use regression::{Audit, CheckError, MissingComparison, Regression, audit};

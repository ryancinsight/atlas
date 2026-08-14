//! Exact Atlas gitlink checkout for sibling Cargo path dependencies.

#![forbid(unsafe_code)]
#![deny(missing_docs)]

mod checkout;
mod error;
mod git;
mod graph;
mod manifest;

pub use checkout::{CheckoutConfig, CheckoutSummary, checkout};
pub use error::CheckoutError;

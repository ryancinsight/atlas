//! Wall-clock budget enforcement for benchmarks and examples.
//!
//! Companion to the regression gate: where the gate classifies Criterion
//! results, this module bounds how long producing them may take. Policy
//! (AGENTS.md `engineering_gates`: runtime budgets): every executable
//! artifact carries a committed finite budget — bench binaries smoke-run in
//! single-iteration mode under the standard test budget, full timing runs
//! and CI-safe examples run under committed wall-clock bounds. A breach is a
//! defect to root-cause (oversized measurement design, or a slow production
//! kernel to optimize) — never resolved by deleting the artifact or raising
//! the bound in the offending diff.
//!
//! Enforcement prepares targets by compiling current source or resolving a
//! retained executable, then directly bounds each binary's execution. The
//! compile phase is unbounded (shared-cache build cost is never charged
//! against the artifact). Executing the binary directly
//! rather than through `cargo` lets the supervisor terminate and reap the
//! benchmark itself. Killing `cargo` can orphan that benchmark. Descendants
//! spawned by an artifact are outside this immediate-child boundary.

mod error;
mod runner;
mod targets;

#[cfg(test)]
mod tests;

use std::path::Path;
use std::time::Duration;

pub use error::BudgetError;
pub use runner::Outcome;
pub use targets::{PreparedTarget, WorkspaceLayout};

/// Selects whether execution uses current sources or an already retained binary.
#[derive(Debug, PartialEq, Eq)]
pub enum TargetSource {
    /// Compile every target selected by the mode, applying the named exclusions.
    Compile {
        /// Targets excluded by name after compilation.
        skip: Vec<String>,
    },
    /// Execute this exact artifact without compiling the workspace.
    Retained(PreparedTarget),
}

/// Enforcement mode selecting the target kind and execution arguments.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Run each bench binary once (`--test`) under the standard test budget.
    Smoke,
    /// Run each bench binary's full Criterion measurement under the
    /// per-binary timing bound.
    Timing,
    /// Run each example binary under the standard test budget.
    Examples,
}

impl Mode {
    /// Default wall-clock bound, derived from the committed gate budgets:
    /// smoke and examples share the 60s test-termination bound, timing runs
    /// use the 300s per-binary bound from the benchmark time model.
    #[must_use]
    pub const fn default_bound(self) -> Duration {
        match self {
            Self::Smoke | Self::Examples => Duration::from_mins(1),
            Self::Timing => Duration::from_mins(5),
        }
    }

    /// Cargo target kind the mode operates on.
    #[must_use]
    pub const fn target_kind(self) -> &'static str {
        match self {
            Self::Smoke | Self::Timing => "bench",
            Self::Examples => "example",
        }
    }

    /// Arguments passed to each executed binary.
    #[must_use]
    pub const fn arguments(self) -> &'static [&'static str] {
        match self {
            // Criterion and libtest harnesses both interpret --test as
            // single-iteration validation mode.
            Self::Smoke => &["--test"],
            // A directly executed Criterion binary with --bench runs its
            // full measurement exactly as under `cargo bench`.
            Self::Timing => &["--bench"],
            Self::Examples => &[],
        }
    }
}

/// One target's budget verdict.
#[derive(Debug, PartialEq, Eq)]
pub struct TargetResult {
    /// Package and target identity plus the executed binary.
    pub target: PreparedTarget,
    /// Terminal outcome of the bounded execution.
    pub outcome: Outcome,
}

/// Complete result of one enforcement run.
#[derive(Debug, PartialEq, Eq)]
pub struct Enforcement {
    /// Mode the run enforced.
    pub mode: Mode,
    /// Wall-clock bound applied to every target.
    pub bound: Duration,
    /// Per-target verdicts in package/name order.
    pub results: Vec<TargetResult>,
    /// Targets excluded by the caller's skip list, in discovery order.
    pub skipped: Vec<String>,
}

impl Enforcement {
    /// True when any target breached its bound or failed to run.
    #[must_use]
    pub fn has_failures(&self) -> bool {
        self.results
            .iter()
            .any(|result| !matches!(result.outcome, Outcome::Clean { .. }))
    }
}

/// Prepares the selected targets and executes each under `bound`.
///
/// Retained paths resolve relative to the invoking process before execution
/// changes to the metadata-resolved workspace directory. The caller owns the
/// artifact's provenance and its correspondence to the recorded target identity.
///
/// # Errors
///
/// Returns [`BudgetError`] when the bound is zero, workspace metadata or the
/// compile phase fails, a retained path is invalid, or a child process cannot
/// be spawned or supervised;
/// per-target breaches and failures are data in the returned
/// [`Enforcement`], not errors.
pub fn enforce(
    manifest_path: &Path,
    mode: Mode,
    bound: Duration,
    source: TargetSource,
) -> Result<Enforcement, BudgetError> {
    if bound.is_zero() {
        return Err(BudgetError::ZeroBound);
    }
    let layout = targets::workspace_layout(manifest_path)?;
    let (prepared, skip) = match source {
        TargetSource::Compile { skip } => (targets::compile_targets(manifest_path, mode)?, skip),
        TargetSource::Retained(target) => (vec![targets::retained_target(target)?], Vec::new()),
    };

    let mut results = Vec::new();
    let mut skipped = Vec::new();
    for target in prepared {
        if skip.iter().any(|name| name == &target.name) {
            skipped.push(target.name);
            continue;
        }
        let outcome = runner::run_bounded(
            &target.name,
            &target.executable,
            mode.arguments(),
            &layout,
            bound,
        )?;
        results.push(TargetResult { target, outcome });
    }
    Ok(Enforcement {
        mode,
        bound,
        results,
        skipped,
    })
}

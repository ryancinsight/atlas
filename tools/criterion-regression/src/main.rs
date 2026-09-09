//! Command-line interface for the Atlas Criterion regression gate.

use std::env;
use std::ffi::OsString;
use std::process::ExitCode;

use atlas_criterion_gate::budget::{self, Enforcement, Outcome};
use atlas_criterion_gate::criterion::{
    Audit, ReplicatedAudit, Replication, audit_replicated_counterbalanced,
    required_confidence_level,
};

mod cli;

use cli::{Command, parse_arguments};

fn main() -> ExitCode {
    match run(env::args_os().skip(1)) {
        Ok(code) => code,
        Err(error) => {
            eprintln!("criterion-regression: {error}");
            ExitCode::from(2)
        }
    }
}

fn run(arguments: impl Iterator<Item = OsString>) -> Result<ExitCode, String> {
    let arguments: Vec<_> = arguments.collect();
    match parse_arguments(&arguments)? {
        Command::RequiredConfidence {
            criterion_root,
            baseline,
        } => {
            let confidence = required_confidence_level(&criterion_root, &baseline)
                .map_err(|error| error.to_string())?;
            println!("{confidence:.17}");
            Ok(ExitCode::SUCCESS)
        }
        Command::CheckReplicatedCounterbalanced {
            first_baseline_first_root,
            first_candidate_first_root,
            second_baseline_first_root,
            second_candidate_first_root,
            baseline,
        } => {
            let result = audit_replicated_counterbalanced(
                &first_baseline_first_root,
                &first_candidate_first_root,
                &second_baseline_first_root,
                &second_candidate_first_root,
                &baseline,
            )
            .map_err(|error| error.to_string())?;
            print_replicated_audit(&result);
            Ok(if result.has_failures() {
                ExitCode::FAILURE
            } else {
                ExitCode::SUCCESS
            })
        }
        Command::EnforceBudget {
            manifest_path,
            mode,
            bound,
            source,
        } => {
            let result = budget::enforce(&manifest_path, mode, bound, source)
                .map_err(|error| error.to_string())?;
            print_enforcement(&result);
            Ok(if result.has_failures() {
                ExitCode::FAILURE
            } else {
                ExitCode::SUCCESS
            })
        }
    }
}

fn print_enforcement(enforcement: &Enforcement) {
    let bound = enforcement.bound.as_secs_f64();
    for result in &enforcement.results {
        let identity = format!("{}/{}", result.target.package, result.target.name);
        match &result.outcome {
            Outcome::Clean { elapsed } => {
                println!("within budget: {identity} {:.1}s", elapsed.as_secs_f64());
            }
            Outcome::Breach { .. } => {
                println!("budget breach: {identity} exceeded {bound:.0}s and was terminated");
            }
            Outcome::RunFailure { code, elapsed } => match code {
                Some(code) => println!(
                    "run failure: {identity} exit code {code} after {:.1}s",
                    elapsed.as_secs_f64()
                ),
                None => println!(
                    "run failure: {identity} terminated by signal after {:.1}s",
                    elapsed.as_secs_f64()
                ),
            },
        }
    }
    for name in &enforcement.skipped {
        println!("skipped by request: {name}");
    }
    let breaches = enforcement
        .results
        .iter()
        .filter(|result| matches!(result.outcome, Outcome::Breach { .. }))
        .count();
    let failures = enforcement
        .results
        .iter()
        .filter(|result| matches!(result.outcome, Outcome::RunFailure { .. }))
        .count();
    println!(
        "budget result: {} target(s) under {bound:.0}s bound, {breaches} breach(es), \
         {failures} run failure(s), {} skipped",
        enforcement.results.len(),
        enforcement.skipped.len(),
    );
}

fn print_replicated_audit(audit: &ReplicatedAudit) {
    print_audit("first", &audit.first);
    print_audit("second", &audit.second);
    for mismatch in &audit.replication_universe_mismatches {
        let replication = match mismatch.present_in {
            Replication::First => "first",
            Replication::Second => "second",
        };
        println!(
            "benchmark only present in {replication} replication: {}",
            mismatch.benchmark.display()
        );
    }
    for regression in &audit.regressions {
        println!(
            "replicated regression: {} first {:+.2}%/{:+.2}%; \
             second {:+.2}%/{:+.2}%",
            regression.benchmark.display(),
            regression.first.baseline_first.point_estimate * 100.0,
            regression.first.candidate_first.point_estimate * 100.0,
            regression.second.baseline_first.point_estimate * 100.0,
            regression.second.candidate_first.point_estimate * 100.0,
        );
    }
    println!(
        "replicated result: {} regression(s), {} replication-universe mismatch(es)",
        audit.regressions.len(),
        audit.replication_universe_mismatches.len(),
    );
}

fn print_audit(replication: &str, audit: &Audit) {
    for regression in &audit.regressions {
        println!(
            "{replication} replication candidate: {} \
             baseline-first {:+.2}% ({:+.2}%..{:+.2}%); \
             candidate-first {:+.2}% ({:+.2}%..{:+.2}%)",
            regression.benchmark.display(),
            regression.baseline_first.point_estimate * 100.0,
            regression.baseline_first.lower_bound * 100.0,
            regression.baseline_first.upper_bound * 100.0,
            regression.candidate_first.point_estimate * 100.0,
            regression.candidate_first.lower_bound * 100.0,
            regression.candidate_first.upper_bound * 100.0,
        );
    }
    for missing in &audit.missing_comparisons {
        println!(
            "missing comparison ({:?}): {}",
            missing.order,
            missing.benchmark.display()
        );
    }
    for mismatch in &audit.universe_mismatches {
        println!(
            "benchmark only present in {:?}: {}",
            mismatch.present_in,
            mismatch.benchmark.display()
        );
    }
    for insufficient in &audit.insufficient_confidence {
        println!(
            "insufficient confidence ({:?}): {} {:.8}% < {:.8}%",
            insufficient.order,
            insufficient.benchmark.display(),
            insufficient.observed * 100.0,
            insufficient.required * 100.0,
        );
    }

    println!(
        "{replication} replication evaluated {} comparison(s) at {:.8}% confidence: \
         {} candidate(s), {} missing, {} universe mismatch(es), \
         {} insufficient-confidence interval(s)",
        audit.comparisons,
        audit.required_confidence_level * 100.0,
        audit.regressions.len(),
        audit.missing_comparisons.len(),
        audit.universe_mismatches.len(),
        audit.insufficient_confidence.len(),
    );
}

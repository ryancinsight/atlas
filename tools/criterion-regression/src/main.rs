//! Command-line interface for the Atlas Criterion regression gate.

use std::env;
use std::ffi::OsString;
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Duration;

use atlas_criterion_gate::budget::{self, Enforcement, Mode, Outcome};
use atlas_criterion_gate::criterion::{
    Audit, ReplicatedAudit, Replication, audit_replicated_counterbalanced,
    required_confidence_level,
};

const USAGE: &str = "\
usage:
  criterion-regression required-confidence \
    --criterion-root <path> --baseline <name>
  criterion-regression check-replicated-counterbalanced \
    --first-baseline-first-root <path> \
    --first-candidate-first-root <path> \
    --second-baseline-first-root <path> \
    --second-candidate-first-root <path> \
    --baseline <name>
  criterion-regression enforce-budget \
    --manifest-path <Cargo.toml> --mode <smoke|timing|examples> \
    [--bound-seconds <n>] [--skip <target>]...

Computes the family-wise confidence requirement, evaluates phase-reversed,
counterbalanced Criterion relative-change confidence intervals, or enforces
wall-clock budgets over bench and example binaries (smoke: one iteration per
bench under 60s; timing: full measurement under 300s; examples: 60s).
";

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
            skip,
        } => {
            let result = budget::enforce(&manifest_path, mode, bound, &skip)
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

#[derive(Debug, PartialEq, Eq)]
enum Command {
    RequiredConfidence {
        criterion_root: PathBuf,
        baseline: String,
    },
    CheckReplicatedCounterbalanced {
        first_baseline_first_root: PathBuf,
        first_candidate_first_root: PathBuf,
        second_baseline_first_root: PathBuf,
        second_candidate_first_root: PathBuf,
        baseline: String,
    },
    EnforceBudget {
        manifest_path: PathBuf,
        mode: Mode,
        bound: Duration,
        skip: Vec<String>,
    },
}

#[derive(Default)]
struct Flags {
    criterion_root: Option<PathBuf>,
    first_baseline_first_root: Option<PathBuf>,
    first_candidate_first_root: Option<PathBuf>,
    second_baseline_first_root: Option<PathBuf>,
    second_candidate_first_root: Option<PathBuf>,
    baseline: Option<String>,
    manifest_path: Option<PathBuf>,
    mode: Option<Mode>,
    bound_seconds: Option<u64>,
    skip: Vec<String>,
}

fn collect_flags(arguments: &[OsString]) -> Result<Flags, String> {
    let mut flags = Flags::default();
    let mut index = 1;
    while index < arguments.len() {
        let Some(flag) = arguments[index].to_str() else {
            return Err(format!("argument is not valid UTF-8\n\n{USAGE}"));
        };
        let Some(value) = arguments.get(index + 1) else {
            return Err(format!("missing value for {flag}\n\n{USAGE}"));
        };
        let text = |label: &str| {
            value
                .to_str()
                .map(str::to_owned)
                .ok_or_else(|| format!("{label} is not valid UTF-8"))
        };

        match flag {
            "--criterion-root" => flags.criterion_root = Some(PathBuf::from(value)),
            "--first-baseline-first-root" => {
                flags.first_baseline_first_root = Some(PathBuf::from(value));
            }
            "--first-candidate-first-root" => {
                flags.first_candidate_first_root = Some(PathBuf::from(value));
            }
            "--second-baseline-first-root" => {
                flags.second_baseline_first_root = Some(PathBuf::from(value));
            }
            "--second-candidate-first-root" => {
                flags.second_candidate_first_root = Some(PathBuf::from(value));
            }
            "--baseline" => flags.baseline = Some(text("baseline name")?),
            "--manifest-path" => flags.manifest_path = Some(PathBuf::from(value)),
            "--mode" => flags.mode = Some(parse_mode(&text("mode")?)?),
            "--bound-seconds" => {
                let text = text("bound")?;
                flags.bound_seconds = Some(
                    text.parse::<u64>()
                        .map_err(|error| format!("invalid --bound-seconds {text:?}: {error}"))?,
                );
            }
            "--skip" => flags.skip.push(text("skip target")?),
            _ => return Err(format!("unknown option {flag:?}\n\n{USAGE}")),
        }
        index += 2;
    }
    Ok(flags)
}

fn parse_arguments(arguments: &[OsString]) -> Result<Command, String> {
    let Some(command) = arguments.first().and_then(|argument| argument.to_str()) else {
        return Err(USAGE.to_owned());
    };
    if !matches!(
        command,
        "required-confidence" | "check-replicated-counterbalanced" | "enforce-budget"
    ) {
        return Err(format!("unknown command {command:?}\n\n{USAGE}"));
    }
    let flags = collect_flags(arguments)?;

    let require_baseline = || {
        flags
            .baseline
            .clone()
            .ok_or_else(|| format!("missing --baseline\n\n{USAGE}"))
    };
    match command {
        "required-confidence" => Ok(Command::RequiredConfidence {
            criterion_root: flags
                .criterion_root
                .ok_or_else(|| format!("missing --criterion-root\n\n{USAGE}"))?,
            baseline: require_baseline()?,
        }),
        "check-replicated-counterbalanced" => Ok(Command::CheckReplicatedCounterbalanced {
            first_baseline_first_root: flags
                .first_baseline_first_root
                .ok_or_else(|| format!("missing --first-baseline-first-root\n\n{USAGE}"))?,
            first_candidate_first_root: flags
                .first_candidate_first_root
                .ok_or_else(|| format!("missing --first-candidate-first-root\n\n{USAGE}"))?,
            second_baseline_first_root: flags
                .second_baseline_first_root
                .ok_or_else(|| format!("missing --second-baseline-first-root\n\n{USAGE}"))?,
            second_candidate_first_root: flags
                .second_candidate_first_root
                .ok_or_else(|| format!("missing --second-candidate-first-root\n\n{USAGE}"))?,
            baseline: require_baseline()?,
        }),
        "enforce-budget" => {
            let mode = flags
                .mode
                .ok_or_else(|| format!("missing --mode\n\n{USAGE}"))?;
            Ok(Command::EnforceBudget {
                manifest_path: flags
                    .manifest_path
                    .ok_or_else(|| format!("missing --manifest-path\n\n{USAGE}"))?,
                mode,
                bound: flags
                    .bound_seconds
                    .map_or(mode.default_bound(), Duration::from_secs),
                skip: flags.skip,
            })
        }
        _ => unreachable!("invariant: command was validated before option parsing"),
    }
}

fn parse_mode(text: &str) -> Result<Mode, String> {
    match text {
        "smoke" => Ok(Mode::Smoke),
        "timing" => Ok(Mode::Timing),
        "examples" => Ok(Mode::Examples),
        other => Err(format!(
            "unknown mode {other:?} (smoke|timing|examples)\n\n{USAGE}"
        )),
    }
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

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;

    #[test]
    fn parses_complete_replicated_counterbalanced_command() {
        let arguments = [
            OsString::from("check-replicated-counterbalanced"),
            OsString::from("--first-baseline-first-root"),
            OsString::from("target/criterion-first-a"),
            OsString::from("--first-candidate-first-root"),
            OsString::from("target/criterion-first-b"),
            OsString::from("--second-baseline-first-root"),
            OsString::from("target/criterion-second-a"),
            OsString::from("--second-candidate-first-root"),
            OsString::from("target/criterion-second-b"),
            OsString::from("--baseline"),
            OsString::from("atlas-base"),
        ];

        let command = parse_arguments(&arguments).unwrap();

        assert_eq!(
            command,
            Command::CheckReplicatedCounterbalanced {
                first_baseline_first_root: PathBuf::from("target/criterion-first-a"),
                first_candidate_first_root: PathBuf::from("target/criterion-first-b"),
                second_baseline_first_root: PathBuf::from("target/criterion-second-a"),
                second_candidate_first_root: PathBuf::from("target/criterion-second-b"),
                baseline: "atlas-base".to_owned(),
            }
        );
    }

    #[test]
    fn parses_required_confidence_command() {
        let arguments = [
            OsString::from("required-confidence"),
            OsString::from("--criterion-root"),
            OsString::from("target/criterion"),
            OsString::from("--baseline"),
            OsString::from("atlas-base"),
        ];

        let command = parse_arguments(&arguments).unwrap();

        assert_eq!(
            command,
            Command::RequiredConfidence {
                criterion_root: PathBuf::from("target/criterion"),
                baseline: "atlas-base".to_owned(),
            }
        );
    }

    #[test]
    fn parses_enforce_budget_with_defaults_and_skips() {
        let arguments = [
            OsString::from("enforce-budget"),
            OsString::from("--manifest-path"),
            OsString::from("repos/themis/Cargo.toml"),
            OsString::from("--mode"),
            OsString::from("timing"),
            OsString::from("--skip"),
            OsString::from("gpu_saturation"),
            OsString::from("--skip"),
            OsString::from("display_demo"),
        ];

        let command = parse_arguments(&arguments).unwrap();

        assert_eq!(
            command,
            Command::EnforceBudget {
                manifest_path: PathBuf::from("repos/themis/Cargo.toml"),
                mode: Mode::Timing,
                bound: Duration::from_mins(5),
                skip: vec!["gpu_saturation".to_owned(), "display_demo".to_owned()],
            }
        );
    }

    #[test]
    fn enforce_budget_explicit_bound_overrides_mode_default() {
        let arguments = [
            OsString::from("enforce-budget"),
            OsString::from("--manifest-path"),
            OsString::from("Cargo.toml"),
            OsString::from("--mode"),
            OsString::from("smoke"),
            OsString::from("--bound-seconds"),
            OsString::from("45"),
        ];

        let command = parse_arguments(&arguments).unwrap();

        let Command::EnforceBudget { bound, mode, .. } = command else {
            panic!("expected EnforceBudget");
        };
        assert_eq!(mode, Mode::Smoke);
        assert_eq!(bound, Duration::from_secs(45));
    }

    #[test]
    fn rejects_unknown_option() {
        let arguments = [
            OsString::from("check-replicated-counterbalanced"),
            OsString::from("--threshold"),
            OsString::from("15"),
        ];

        let error = parse_arguments(&arguments).unwrap_err();

        assert!(error.contains("unknown option \"--threshold\""));
    }
}

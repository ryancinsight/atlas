//! Command-line interface for the Atlas Criterion regression gate.

use std::env;
use std::ffi::OsString;
use std::path::PathBuf;
use std::process::ExitCode;

use atlas_criterion_gate::criterion::{Audit, audit_counterbalanced, required_confidence_level};

const USAGE: &str = "\
usage:
  criterion-regression required-confidence \
    --criterion-root <path> --baseline <name>
  criterion-regression check-counterbalanced \
    --baseline-first-root <path> --candidate-first-root <path> \
    --baseline <name>

Computes the family-wise confidence requirement or evaluates opposite-order
Criterion relative-change confidence intervals.
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
        Command::CheckCounterbalanced {
            baseline_first_root,
            candidate_first_root,
            baseline,
        } => {
            let result =
                audit_counterbalanced(&baseline_first_root, &candidate_first_root, &baseline)
                    .map_err(|error| error.to_string())?;
            print_audit(&result);
            Ok(if result.has_failures() {
                ExitCode::FAILURE
            } else {
                ExitCode::SUCCESS
            })
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
enum Command {
    RequiredConfidence {
        criterion_root: PathBuf,
        baseline: String,
    },
    CheckCounterbalanced {
        baseline_first_root: PathBuf,
        candidate_first_root: PathBuf,
        baseline: String,
    },
}

fn parse_arguments(arguments: &[OsString]) -> Result<Command, String> {
    let Some(command) = arguments.first().and_then(|argument| argument.to_str()) else {
        return Err(USAGE.to_owned());
    };
    if !matches!(command, "required-confidence" | "check-counterbalanced") {
        return Err(format!("unknown command {command:?}\n\n{USAGE}"));
    }

    let mut criterion_root = None;
    let mut baseline_first_root = None;
    let mut candidate_first_root = None;
    let mut baseline = None;
    let mut index = 1;
    while index < arguments.len() {
        let Some(flag) = arguments[index].to_str() else {
            return Err(format!("argument is not valid UTF-8\n\n{USAGE}"));
        };
        let Some(value) = arguments.get(index + 1) else {
            return Err(format!("missing value for {flag}\n\n{USAGE}"));
        };

        match flag {
            "--criterion-root" => criterion_root = Some(PathBuf::from(value)),
            "--baseline-first-root" => baseline_first_root = Some(PathBuf::from(value)),
            "--candidate-first-root" => candidate_first_root = Some(PathBuf::from(value)),
            "--baseline" => {
                baseline = Some(
                    value
                        .to_str()
                        .ok_or_else(|| "baseline name is not valid UTF-8".to_owned())?
                        .to_owned(),
                );
            }
            _ => return Err(format!("unknown option {flag:?}\n\n{USAGE}")),
        }
        index += 2;
    }

    let baseline = baseline.ok_or_else(|| format!("missing --baseline\n\n{USAGE}"))?;
    match command {
        "required-confidence" => Ok(Command::RequiredConfidence {
            criterion_root: criterion_root
                .ok_or_else(|| format!("missing --criterion-root\n\n{USAGE}"))?,
            baseline,
        }),
        "check-counterbalanced" => Ok(Command::CheckCounterbalanced {
            baseline_first_root: baseline_first_root
                .ok_or_else(|| format!("missing --baseline-first-root\n\n{USAGE}"))?,
            candidate_first_root: candidate_first_root
                .ok_or_else(|| format!("missing --candidate-first-root\n\n{USAGE}"))?,
            baseline,
        }),
        _ => unreachable!("invariant: command was validated before option parsing"),
    }
}

fn print_audit(audit: &Audit) {
    for regression in &audit.regressions {
        println!(
            "regression: {} baseline-first {:+.2}% ({:+.2}%..{:+.2}%); \
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
        "evaluated {} counterbalanced comparison(s) at {:.8}% confidence: \
         {} regression(s), {} missing, {} universe mismatch(es), \
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
    fn parses_complete_counterbalanced_command() {
        let arguments = [
            OsString::from("check-counterbalanced"),
            OsString::from("--baseline-first-root"),
            OsString::from("target/criterion-a"),
            OsString::from("--candidate-first-root"),
            OsString::from("target/criterion-b"),
            OsString::from("--baseline"),
            OsString::from("atlas-base"),
        ];

        let command = parse_arguments(&arguments).unwrap();

        assert_eq!(
            command,
            Command::CheckCounterbalanced {
                baseline_first_root: PathBuf::from("target/criterion-a"),
                candidate_first_root: PathBuf::from("target/criterion-b"),
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
    fn rejects_unknown_option() {
        let arguments = [
            OsString::from("check-counterbalanced"),
            OsString::from("--threshold"),
            OsString::from("15"),
        ];

        let error = parse_arguments(&arguments).unwrap_err();

        assert!(error.contains("unknown option \"--threshold\""));
    }
}

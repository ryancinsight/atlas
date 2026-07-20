//! Command-line interface for the Atlas Criterion regression gate.

use std::env;
use std::ffi::OsString;
use std::path::PathBuf;
use std::process::ExitCode;

use atlas_criterion_gate::criterion::{Audit, audit};

const USAGE: &str = "\
usage: criterion-regression check --workspace <path> --baseline <name>

Evaluates Criterion relative-change confidence intervals produced by running
the head benchmarks with `--baseline <name>`.
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
    let (workspace, baseline) = parse_arguments(&arguments)?;
    let result = audit(&workspace, &baseline).map_err(|error| error.to_string())?;
    print_audit(&result);
    Ok(if result.has_failures() {
        ExitCode::FAILURE
    } else {
        ExitCode::SUCCESS
    })
}

fn parse_arguments(arguments: &[OsString]) -> Result<(PathBuf, String), String> {
    let Some(command) = arguments.first().and_then(|argument| argument.to_str()) else {
        return Err(USAGE.to_owned());
    };
    if command != "check" {
        return Err(format!("unknown command {command:?}\n\n{USAGE}"));
    }

    let mut workspace = None;
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
            "--workspace" => workspace = Some(PathBuf::from(value)),
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

    let workspace = workspace.ok_or_else(|| format!("missing --workspace\n\n{USAGE}"))?;
    let baseline = baseline.ok_or_else(|| format!("missing --baseline\n\n{USAGE}"))?;
    Ok((workspace, baseline))
}

fn print_audit(audit: &Audit) {
    for regression in &audit.regressions {
        println!(
            "regression: {} median {:+.2}% ({:.0}% CI {:+.2}%..{:+.2}%)",
            regression.benchmark.display(),
            regression.point_estimate * 100.0,
            regression.confidence_level * 100.0,
            regression.lower_bound * 100.0,
            regression.upper_bound * 100.0,
        );
    }
    for missing in &audit.missing_comparisons {
        println!("missing comparison: {}", missing.benchmark.display());
    }

    println!(
        "evaluated {} comparison(s): {} regression(s), {} missing",
        audit.comparisons,
        audit.regressions.len(),
        audit.missing_comparisons.len(),
    );
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;

    #[test]
    fn parses_complete_check_command() {
        let arguments = [
            OsString::from("check"),
            OsString::from("--workspace"),
            OsString::from("."),
            OsString::from("--baseline"),
            OsString::from("atlas-base"),
        ];

        let (workspace, baseline) = parse_arguments(&arguments).unwrap();

        assert_eq!(workspace, PathBuf::from("."));
        assert_eq!(baseline, "atlas-base");
    }

    #[test]
    fn rejects_unknown_option() {
        let arguments = [
            OsString::from("check"),
            OsString::from("--threshold"),
            OsString::from("15"),
        ];

        let error = parse_arguments(&arguments).unwrap_err();

        assert!(error.contains("unknown option \"--threshold\""));
    }
}

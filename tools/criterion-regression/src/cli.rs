use std::ffi::OsString;
use std::path::PathBuf;
use std::time::Duration;

use atlas_criterion_gate::budget::{Mode, PreparedTarget, TargetSource};

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
    [--executable <path> --package <name> --target <name>]

Computes the family-wise confidence requirement, evaluates phase-reversed,
counterbalanced Criterion relative-change confidence intervals, or enforces
wall-clock budgets over bench and example binaries (smoke: one iteration per
bench under 60s; timing: full measurement under 300s; examples: 60s).
";

#[derive(Debug, PartialEq, Eq)]
pub(super) enum Command {
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
        source: TargetSource,
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
    executable: Option<PathBuf>,
    package: Option<String>,
    target: Option<String>,
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
            "--executable" => flags.executable = Some(PathBuf::from(value)),
            "--package" => flags.package = Some(text("package name")?),
            "--target" => flags.target = Some(text("target name")?),
            _ => return Err(format!("unknown option {flag:?}\n\n{USAGE}")),
        }
        index += 2;
    }
    Ok(flags)
}

pub(super) fn parse_arguments(arguments: &[OsString]) -> Result<Command, String> {
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
    if command != "enforce-budget"
        && (flags.executable.is_some() || flags.package.is_some() || flags.target.is_some())
    {
        return Err("--executable, --package, and --target require enforce-budget".to_owned());
    }

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
            let source = match (flags.executable, flags.package, flags.target) {
                (None, None, None) => TargetSource::Compile { skip: flags.skip },
                (Some(executable), Some(package), Some(name)) => {
                    if !flags.skip.is_empty() {
                        return Err("--skip cannot be combined with --executable".to_owned());
                    }
                    if package.is_empty() || name.is_empty() {
                        return Err(
                            "retained package and target names must not be empty".to_owned()
                        );
                    }
                    TargetSource::Retained(PreparedTarget {
                        package,
                        name,
                        executable,
                    })
                }
                _ => {
                    return Err(
                        "--executable, --package, and --target must be supplied together"
                            .to_owned(),
                    );
                }
            };
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
                source,
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
                source: TargetSource::Compile {
                    skip: vec!["gpu_saturation".to_owned(), "display_demo".to_owned()],
                },
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
    fn parses_retained_target_for_each_mode_without_changing_bounds() {
        for (name, mode) in [
            ("smoke", Mode::Smoke),
            ("timing", Mode::Timing),
            ("examples", Mode::Examples),
        ] {
            let arguments = [
                "enforce-budget",
                "--manifest-path",
                "Cargo.toml",
                "--mode",
                name,
                "--executable",
                "output/retained bench",
                "--package",
                "apollo",
                "--target",
                "fft",
            ]
            .map(OsString::from);
            assert_eq!(
                parse_arguments(&arguments).unwrap(),
                Command::EnforceBudget {
                    manifest_path: PathBuf::from("Cargo.toml"),
                    mode,
                    bound: mode.default_bound(),
                    source: TargetSource::Retained(PreparedTarget {
                        package: "apollo".to_owned(),
                        name: "fft".to_owned(),
                        executable: PathBuf::from("output/retained bench"),
                    }),
                }
            );
        }
    }

    #[test]
    fn rejects_incomplete_retained_selections() {
        for selection in 1..7 {
            let mut arguments = [
                "enforce-budget",
                "--manifest-path",
                "Cargo.toml",
                "--mode",
                "timing",
            ]
            .map(OsString::from)
            .to_vec();
            for (index, pair) in [
                ["--executable", "bench"],
                ["--package", "apollo"],
                ["--target", "fft"],
            ]
            .into_iter()
            .enumerate()
            {
                if selection & (1 << index) != 0 {
                    arguments.extend(pair.map(OsString::from));
                }
            }
            assert_eq!(
                parse_arguments(&arguments).unwrap_err(),
                "--executable, --package, and --target must be supplied together"
            );
        }
    }

    #[test]
    fn rejects_retained_exclusions_and_empty_identity() {
        let arguments = [
            "enforce-budget",
            "--manifest-path",
            "Cargo.toml",
            "--mode",
            "timing",
            "--executable",
            "bench",
            "--package",
            "apollo",
            "--target",
            "fft",
        ]
        .map(OsString::from);
        let mut skipped = arguments.to_vec();
        skipped.extend(["--skip", "fft"].map(OsString::from));
        assert_eq!(
            parse_arguments(&skipped).unwrap_err(),
            "--skip cannot be combined with --executable"
        );
        for index in [8, 10] {
            let mut empty = arguments.clone();
            empty[index] = OsString::new();
            assert_eq!(
                parse_arguments(&empty).unwrap_err(),
                "retained package and target names must not be empty"
            );
        }
    }

    #[test]
    fn rejects_retained_options_on_statistical_commands() {
        let arguments = [
            "required-confidence",
            "--criterion-root",
            "target/criterion",
            "--baseline",
            "base",
            "--target",
            "fft",
        ]
        .map(OsString::from);
        assert_eq!(
            parse_arguments(&arguments).unwrap_err(),
            "--executable, --package, and --target require enforce-budget"
        );
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

//! Command-line interface for the Atlas manifest-version guard.
//!
//! See the library docs at [`atlas_version_guard`] for the audit contract,
//! exit codes, and the read-only probe design.
//!
//! # Synopsis
//!
//! ```text
//! version-guard coherence --atlas-root <path> [--format human|json]
//! version-guard scan --repo <path> [--range <git-rev-spec>] \
//!                   [--format human|json] [--commit-msg <path>]
//! ```
//!
//! The guard never mutates the repository under audit. `scan` invokes
//! `git diff <range> -- '*.toml'` (read-only) and parses the resulting diff
//! text. `coherence` scans checked-in manifests under the Atlas root and
//! reports first-party requirement/version mismatches, plus any member whose
//! working tree is behind the branch it tracks — the manifests of such a
//! member describe an older state than the stack publishes, so a verdict about
//! it is measured against the wrong versions. Run `git fetch` across the
//! members first; reading a remote-tracking ref is local. If `--commit-msg
//! <path>` is supplied, the message body is read from that path; otherwise
//! `scan` reads `git log -1 --format=%B <range>` to fetch the commit message
//! of the head of the range.

use std::env;
use std::ffi::OsString;
use std::path::PathBuf;
use std::process::{Command, ExitCode};

use atlas_version_guard::classify::classify_intent;
use atlas_version_guard::coherence::scan_atlas;
use atlas_version_guard::error::Error;
use atlas_version_guard::report::{Format, Report};
use atlas_version_guard::scan::{has_defect, scan_diff};

const USAGE: &str = "\
usage:
  version-guard coherence --atlas-root <path> [--format human|json]
  version-guard scan --repo <path> [--range <git-rev-spec>] \
                     [--format human|json] [--commit-msg <path>]

`coherence` scans checked-in manifests under the Atlas root and reports
first-party requirement/version mismatches. `scan` reads the diff over
`<range>` (default HEAD~1..HEAD) of `*.toml` files in `<repo>` and
classifies every touched `version =` line as Identical, Forward, or
Backward. A Forward bump without a declared release intent
(`chore(release)`, `build(deps)`, `Bump:` trailer, or `BREAKING CHANGE:`
footer) is a defect; a Backward movement is always a defect. A declared
release/bump with no forward version movement is a defect, including an
empty or identical-only diff.

The --commit-msg path is optional; if omitted, the message body for the head
of the range is read via `git log -1 --format=%B`.

Exit codes:
  0  no defects (no declared release without a forward version movement, and
     every touched line is identical or forward-with-intent)
  1  defect detected (at least one backward movement, or one forward movement
     without declared intent)
  2  invocation error (bad CLI, git plumbing failure, missing file)
";

/// Entry point. Parses argv and dispatches to the scan body.
#[must_use]
pub fn main() -> ExitCode {
    match run(env::args_os().skip(1)) {
        Ok(code) => code,
        Err(err) => {
            eprintln!("version-guard: {err}");
            ExitCode::from(2)
        }
    }
}

fn run(arguments: impl Iterator<Item = OsString>) -> Result<ExitCode, Error> {
    let parsed = parse_arguments(arguments)?;
    let Parsed {
        subcommand,
        repo,
        atlas_root,
        range,
        format,
        commit_msg_path,
    } = parsed;
    match subcommand {
        Subcommand::Scan => {
            let repo = repo.ok_or_else(|| Error::Git {
                command: "argv".to_string(),
                stderr: "missing required --repo <path>".to_string(),
            })?;
            let range = range.unwrap_or_else(|| "HEAD~1..HEAD".to_string());
            let diff_text = git_diff_toml(&repo, &range)?;
            let commit_msg = match commit_msg_path {
                Some(path) => std::fs::read_to_string(&path)?,
                None => git_commit_message(&repo, &range)?,
            };
            let findings = scan_diff(&diff_text, &commit_msg);
            let intent = classify_intent(&commit_msg);
            let report = Report::new(&findings, intent);
            print!("{}", report.render(format));
            if has_defect(&findings, intent) {
                Ok(ExitCode::from(1))
            } else {
                Ok(ExitCode::SUCCESS)
            }
        }
        Subcommand::Coherence => {
            let atlas_root = atlas_root.ok_or_else(|| Error::Manifest {
                path: String::from("argv"),
                message: String::from("missing required --atlas-root <path>"),
            })?;
            let report = scan_atlas(&atlas_root)?;
            print!("{}", report.render(format));
            if report.has_defect() {
                Ok(ExitCode::from(1))
            } else {
                Ok(ExitCode::SUCCESS)
            }
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Subcommand {
    Scan,
    Coherence,
}

struct Parsed {
    subcommand: Subcommand,
    repo: Option<PathBuf>,
    atlas_root: Option<PathBuf>,
    range: Option<String>,
    format: Format,
    commit_msg_path: Option<PathBuf>,
}

fn parse_arguments(arguments: impl Iterator<Item = OsString>) -> Result<Parsed, Error> {
    let args: Vec<OsString> = arguments.collect();
    let mut repo: Option<PathBuf> = None;
    let mut atlas_root: Option<PathBuf> = None;
    let mut range: Option<String> = None;
    let mut format: Format = Format::Human;
    let mut commit_msg_path: Option<PathBuf> = None;
    let mut subcommand: Option<Subcommand> = None;
    let mut idx = 0;
    while idx < args.len() {
        let raw = &args[idx];
        let text = raw.to_string_lossy().into_owned();
        match text.as_str() {
            "--help" | "-h" => {
                print!("{USAGE}");
                std::process::exit(0);
            }
            "--repo" => repo = Some(PathBuf::from(git_flag_value(&args, &mut idx, "--repo")?)),
            "--atlas-root" => atlas_root = Some(PathBuf::from(atlas_root_value(&args, &mut idx)?)),
            "--range" => {
                let value = git_flag_value(&args, &mut idx, "--range")?;
                range = Some(value.to_string_lossy().into_owned());
            }
            "--format" => {
                let v_owned = git_flag_value(&args, &mut idx, "--format")?
                    .to_string_lossy()
                    .into_owned();
                format =
                    Format::from_str_value(&v_owned).ok_or(Error::Format { value: v_owned })?;
            }
            "--commit-msg" => {
                let value = git_flag_value(&args, &mut idx, "--commit-msg")?;
                commit_msg_path = Some(PathBuf::from(value));
            }
            "scan" => subcommand = Some(choose_subcommand(subcommand, Subcommand::Scan)?),
            "coherence" => subcommand = Some(choose_subcommand(subcommand, Subcommand::Coherence)?),
            other => {
                if other.is_empty() {
                    idx += 1;
                    continue;
                }
                return Err(Error::Git {
                    command: "argv".to_string(),
                    stderr: format!("unknown argument or subcommand `{other}`"),
                });
            }
        }
        idx += 1;
    }
    let subcommand = subcommand.unwrap_or(Subcommand::Scan);
    if matches!(subcommand, Subcommand::Scan) && repo.is_none() {
        return Err(Error::Git {
            command: "argv".to_string(),
            stderr: "missing required --repo <path>".to_string(),
        });
    }
    if matches!(subcommand, Subcommand::Coherence) && atlas_root.is_none() {
        return Err(Error::Manifest {
            path: String::from("argv"),
            message: String::from("missing required --atlas-root <path>"),
        });
    }
    Ok(Parsed {
        subcommand,
        repo,
        atlas_root,
        range,
        format,
        commit_msg_path,
    })
}

/// Read the argument following `flag` at `index`, advancing `index`.
fn git_flag_value(args: &[OsString], index: &mut usize, flag: &str) -> Result<OsString, Error> {
    *index += 1;
    args.get(*index).cloned().ok_or_else(|| Error::Git {
        command: "argv".to_string(),
        stderr: format!("{flag} requires a value argument"),
    })
}

/// Read the argument following `--atlas-root` at `index`, advancing `index`.
fn atlas_root_value(args: &[OsString], index: &mut usize) -> Result<OsString, Error> {
    *index += 1;
    args.get(*index).cloned().ok_or_else(|| Error::Manifest {
        path: String::from("argv"),
        message: String::from("--atlas-root requires a path argument"),
    })
}

/// Reject a second subcommand that disagrees with the first one seen.
fn choose_subcommand(current: Option<Subcommand>, next: Subcommand) -> Result<Subcommand, Error> {
    if let Some(existing) = current
        && existing != next
    {
        return Err(Error::Git {
            command: "argv".to_string(),
            stderr: "conflicting subcommands `scan` and `coherence`".to_string(),
        });
    }
    Ok(next)
}

/// Invoke `git diff <range> -- '*.toml'` in `repo` and return the stdout
/// text. The diff is invoked with `--unified=0` to keep the output small
/// (context lines are noise for the version-line scan).
fn git_diff_toml(repo: &PathBuf, range: &str) -> Result<String, Error> {
    let output = Command::new("git")
        .arg("--no-pager")
        .arg("-C")
        .arg(repo)
        .arg("diff")
        .arg("--unified=0")
        .arg(range)
        .arg("--")
        .arg("*.toml")
        .output()?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
        return Err(Error::Git {
            command: format!(
                "git -C {} diff --unified=0 {} -- '*.toml'",
                repo.display(),
                range
            ),
            stderr,
        });
    }
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

/// Invoke `git log -1 --format=%B <range>tail` in `repo` and return the
/// message body. The `<range>tail` form takes the head of the range (the
/// right-hand side of `A..B`) so a multi-commit range yields B's message.
fn git_commit_message(repo: &PathBuf, range: &str) -> Result<String, Error> {
    // The `--right-only` flag with `-1` collapses to the head commit.
    let head = range
        .split("..")
        .last()
        .filter(|s| !s.is_empty())
        .unwrap_or("HEAD");
    let output = Command::new("git")
        .arg("--no-pager")
        .arg("-C")
        .arg(repo)
        .arg("log")
        .arg("-1")
        .arg("--format=%B")
        .arg(head)
        .output()?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
        return Err(Error::Git {
            command: format!("git -C {} log -1 --format=%B {}", repo.display(), head),
            stderr,
        });
    }
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

#[cfg(test)]
#[expect(
    clippy::unwrap_used,
    reason = "test fixtures are known-good; a failure here is a broken test, and panicking names it immediately"
)]
mod tests {
    use super::*;

    #[test]
    fn parse_requires_repo() {
        let err = parse_arguments(["scan".into()].into_iter());
        assert!(err.is_err());
    }

    #[test]
    fn parse_accepts_minimal_scan() {
        let parsed =
            parse_arguments(["scan".into(), "--repo".into(), "/tmp/x".into()].into_iter()).unwrap();
        assert_eq!(parsed.subcommand, Subcommand::Scan);
        assert_eq!(parsed.repo, Some(PathBuf::from("/tmp/x")));
        assert_eq!(parsed.range, None);
        assert_eq!(parsed.format, Format::Human);
        assert!(parsed.commit_msg_path.is_none());
    }

    #[test]
    fn parse_accepts_minimal_coherence() {
        let parsed = parse_arguments(
            [
                "coherence".into(),
                "--atlas-root".into(),
                "/tmp/atlas".into(),
            ]
            .into_iter(),
        )
        .unwrap();
        assert_eq!(parsed.subcommand, Subcommand::Coherence);
        assert_eq!(parsed.atlas_root, Some(PathBuf::from("/tmp/atlas")));
        assert!(parsed.repo.is_none());
    }

    #[test]
    fn parse_rejects_unknown_format() {
        let err = parse_arguments(
            [
                "scan".into(),
                "--repo".into(),
                "/tmp/x".into(),
                "--format".into(),
                "yaml".into(),
            ]
            .into_iter(),
        );
        assert!(err.is_err());
    }
}

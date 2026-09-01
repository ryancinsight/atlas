//! Command-line interface for the Atlas gitlink coherence auditor.
//!
//! See the library docs at [`atlas_gitlink_coherence_gate`] for the audit
//! contract, exit codes, and the read-only probe design.
//!
//! # Synopsis
//!
//! ```text
//! gitlink-coherence audit [--atlas-root <path>] \
//!                        [--format human|markdown|json] \
//!                        [--target-repo <bare-name>]
//! ```
//!
//! The auditor never mutates a member-repo working tree. The caller is
//! responsible for fetching each member's `origin/main` first when they
//! want fresh upstream state.

use std::env;
use std::ffi::OsString;
use std::fs;
use std::path::PathBuf;
use std::process::ExitCode;

use atlas_gitlink_coherence_gate::coherence::{audit, audit_one};
use atlas_gitlink_coherence_gate::error::Error;
use atlas_gitlink_coherence_gate::gitmodules::GitmodulesTable;
use atlas_gitlink_coherence_gate::report::{Format, Report};

const USAGE: &str = "\
usage:
  gitlink-coherence audit [--atlas-root <path>] \
                          [--format human|markdown|json] \
                          [--target-repo <bare-name>] \
                          [--fetch]

Reads <atlas-root>/.gitmodules and probes each pinned gitlink for coherence
against the member's `origin/main`. By default the probe is fully read-only
(no `git fetch`); pass `--fetch` to refresh `refs/remotes/origin/main` from
each member's remote before probing (no working-tree mutation).

Exit codes:
  0  all probed gitlinks are coherent (possibly with stale-advanceable rows)
  1  one or more coherence defects detected (categories A/B/C,
     no-origin-main, unreachable, not-an-object)
  2  invocation error (cli, missing .gitmodules, git plumbing failure)
";

/// Entry point. Parses argv and dispatches to the audit body.
#[must_use]
pub fn main() -> ExitCode {
    match run(env::args_os().skip(1)) {
        Ok(code) => code,
        Err(err) => {
            eprintln!("gitlink-coherence: {err}");
            ExitCode::from(2)
        }
    }
}

fn run(arguments: impl Iterator<Item = OsString>) -> Result<ExitCode, Error> {
    let parsed = parse_arguments(arguments)?;
    let Parsed {
        atlas_root,
        format,
        target_repo,
        fetch,
    } = parsed;
    let atlas_root = atlas_root.unwrap_or_else(|| {
        // Default to the CWD (`D:+atlas` for the coordinator). This is the
        // most friendly default for the on-host usage pattern.
        env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
    });
    let gitmodules_path = atlas_root.join(".gitmodules");
    let bytes = fs::read(&gitmodules_path).map_err(Error::MissingGitmodules)?;
    let text = String::from_utf8(bytes).map_err(|err| Error::GitExit {
        context: "read .gitmodules",
        code: 0,
        stderr: err.to_string(),
    })?;
    let table: GitmodulesTable = text
        .parse::<GitmodulesTable>()
        .map_err(|err| Error::ParseGitmodules(err.to_string()))?;

    let coherence = match target_repo.as_deref() {
        Some(bare) => {
            let sub = table
                .find_by_bare_name(bare)
                .ok_or_else(|| Error::UnknownTargetRepo(bare.to_string()))?;
            let probe = audit_one(&atlas_root, sub, fetch)?;
            atlas_gitlink_coherence_gate::coherence::Coherence {
                probes: vec![probe],
            }
        }
        None => audit(&atlas_root, &table, fetch)?,
    };

    let report = Report::from(&coherence);
    print!("{}", report.render(format));
    if report.defects > 0 {
        Ok(ExitCode::from(1))
    } else {
        Ok(ExitCode::SUCCESS)
    }
}

struct Parsed {
    atlas_root: Option<PathBuf>,
    format: Format,
    target_repo: Option<String>,
    /// Whether to `git fetch` each member before probing.
    fetch: bool,
}

fn parse_arguments(arguments: impl Iterator<Item = OsString>) -> Result<Parsed, Error> {
    let mut atlas_root: Option<PathBuf> = None;
    let mut format: Format = Format::Human;
    let mut target_repo: Option<String> = None;
    let mut fetch: bool = false;
    let mut subcommand: Option<&'static str> = None;

    let args: Vec<OsString> = arguments.collect();
    let mut idx = 0;
    while idx < args.len() {
        let raw = &args[idx];
        let text = raw.to_string_lossy().into_owned();
        match text.as_str() {
            "--help" | "-h" => {
                print!("{USAGE}");
                std::process::exit(0);
            }
            "--atlas-root" => {
                idx += 1;
                let v = args.get(idx).ok_or_else(|| Error::GitExit {
                    context: "argv",
                    code: 0,
                    stderr: "--atlas-root requires a path argument".to_string(),
                })?;
                atlas_root = Some(PathBuf::from(v));
            }
            "--format" => {
                idx += 1;
                let v = args
                    .get(idx)
                    .ok_or_else(|| Error::GitExit {
                        context: "argv",
                        code: 0,
                        stderr: "--format requires a value".to_string(),
                    })?
                    .to_string_lossy()
                    .into_owned();
                format = Format::from_str_value(&v).map_err(|e| Error::GitExit {
                    context: "argv",
                    code: 0,
                    stderr: e,
                })?;
            }
            "--target-repo" => {
                idx += 1;
                let v = args
                    .get(idx)
                    .ok_or_else(|| Error::GitExit {
                        context: "argv",
                        code: 0,
                        stderr: "--target-repo requires a value".to_string(),
                    })?
                    .to_string_lossy()
                    .into_owned();
                target_repo = Some(v);
            }
            "--fetch" => {
                fetch = true;
            }
            "audit" if subcommand.is_none() => {
                subcommand = Some("audit");
            }
            other => {
                if other.is_empty() {
                    idx += 1;
                    continue;
                }
                return Err(Error::GitExit {
                    context: "argv",
                    code: 0,
                    stderr: format!("unknown argument or subcommand `{other}`"),
                });
            }
        }
        idx += 1;
    }

    if subcommand.is_none() {
        // The default action when no subcommand is supplied is `audit`,
        // matching the most ergonomic on-host usage pattern.
    }
    Ok(Parsed {
        atlas_root,
        format,
        target_repo,
        fetch,
    })
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;
    use std::fs;

    #[test]
    fn ambiguous_target_repo_is_reported_as_a_unique_selection_error() {
        let root =
            std::env::temp_dir().join(format!("gitlink-coherence-cli-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(&root).unwrap();
        fs::write(
            root.join(".gitmodules"),
            "[submodule \"repos/left/coeus\"]\n    path = repos/left/coeus\n    url = https://example/left\n\n[submodule \"repos/right/coeus\"]\n    path = repos/right/coeus\n    url = https://example/right\n",
        )
        .unwrap();

        let result = run([
            OsString::from("audit"),
            OsString::from("--atlas-root"),
            root.as_os_str().to_os_string(),
            OsString::from("--target-repo"),
            OsString::from("coeus"),
        ]
        .into_iter());

        let error = result.expect_err("ambiguous target must fail closed");
        assert!(matches!(&error, Error::UnknownTargetRepo(name) if name == "coeus"));
        assert!(
            error.to_string().contains("no unique"),
            "diagnostic was: {error}"
        );
        let _ = fs::remove_dir_all(root);
    }
}

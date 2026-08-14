use std::io;
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

use super::error::BudgetError;
use super::targets::WorkspaceLayout;

/// Terminal result of one bounded execution.
#[derive(Debug, PartialEq, Eq)]
pub enum Outcome {
    /// The target exited successfully inside the bound.
    Clean {
        /// Observed wall-clock runtime.
        elapsed: Duration,
    },
    /// The target exceeded the bound and was terminated.
    Breach {
        /// Wall-clock bound the target failed to meet.
        bound: Duration,
    },
    /// The target exited unsuccessfully inside the bound.
    RunFailure {
        /// Exit code when the operating system reports one.
        code: Option<i32>,
        /// Observed wall-clock runtime.
        elapsed: Duration,
    },
}

/// Poll cadence for the supervision loop. The granularity error it introduces
/// (at most one interval past the bound) is negligible against second-scale
/// bounds and avoids platform-specific waitable-timer plumbing.
const POLL_INTERVAL: Duration = Duration::from_millis(25);

/// Runs `executable` with `arguments` under `bound`, killing it on breach.
///
/// The child runs from the workspace root with `CARGO_TARGET_DIR` pinned to
/// the resolved shared target directory, so a directly executed Criterion
/// binary writes its report tree below the shared cache instead of minting a
/// repo-local `target/`.
pub fn run_bounded(
    target: &str,
    executable: &Path,
    arguments: &[&str],
    layout: &WorkspaceLayout,
    bound: Duration,
) -> Result<Outcome, BudgetError> {
    let child = Command::new(executable)
        .args(arguments)
        .current_dir(&layout.workspace_root)
        .env("CARGO_TARGET_DIR", &layout.target_directory)
        .stdin(Stdio::null())
        .spawn()
        .map_err(|source| BudgetError::Spawn {
            target: target.to_owned(),
            executable: executable.to_path_buf(),
            source,
        })?;
    supervise(target, child, bound)
}

fn supervise(target: &str, mut child: Child, bound: Duration) -> Result<Outcome, BudgetError> {
    let started = Instant::now();
    loop {
        let status = child.try_wait().map_err(|source| BudgetError::Supervise {
            target: target.to_owned(),
            source,
        })?;
        if let Some(status) = status {
            let elapsed = started.elapsed();
            return Ok(if status.success() {
                Outcome::Clean { elapsed }
            } else {
                Outcome::RunFailure {
                    code: status.code(),
                    elapsed,
                }
            });
        }
        if started.elapsed() >= bound {
            terminate(target, &mut child)?;
            return Ok(Outcome::Breach { bound });
        }
        std::thread::sleep(POLL_INTERVAL);
    }
}

fn terminate(target: &str, child: &mut Child) -> Result<(), BudgetError> {
    match child.kill() {
        Ok(()) => {}
        // The child won the race and exited between try_wait and kill.
        Err(error) if error.kind() == io::ErrorKind::InvalidInput => {}
        Err(source) => {
            return Err(BudgetError::Supervise {
                target: target.to_owned(),
                source,
            });
        }
    }
    child.wait().map_err(|source| BudgetError::Supervise {
        target: target.to_owned(),
        source,
    })?;
    Ok(())
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;

    // These tests exercise the wall-clock supervisor itself, so a deliberately
    // blocking child is the adversarial input and the assertion is the kill
    // outcome, not a timing measurement; tiny bounds keep them fast.

    fn shell(script: &str) -> Child {
        #[cfg(windows)]
        {
            Command::new("powershell")
                .args(["-NoProfile", "-Command", script])
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .unwrap()
        }
        #[cfg(not(windows))]
        {
            Command::new("sh")
                .args(["-c", script])
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .unwrap()
        }
    }

    #[test]
    fn breaching_child_is_terminated() {
        #[cfg(windows)]
        let child = shell("Start-Sleep -Seconds 30");
        #[cfg(not(windows))]
        let child = shell("sleep 30");

        let outcome = supervise("sleeper", child, Duration::from_millis(200)).unwrap();

        assert_eq!(
            outcome,
            Outcome::Breach {
                bound: Duration::from_millis(200)
            }
        );
    }

    #[test]
    fn clean_child_reports_success() {
        let child = shell("exit 0");

        let outcome = supervise("quick", child, Duration::from_secs(30)).unwrap();

        assert!(matches!(outcome, Outcome::Clean { .. }));
    }

    #[test]
    fn failing_child_reports_its_exit_code() {
        let child = shell("exit 3");

        let outcome = supervise("failing", child, Duration::from_secs(30)).unwrap();

        let Outcome::RunFailure { code, .. } = outcome else {
            panic!("expected RunFailure, got {outcome:?}");
        };
        assert_eq!(code, Some(3));
    }
}

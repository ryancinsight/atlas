use std::ffi::{OsStr, OsString};
use std::path::Path;
use std::process::{Command, Output};

use crate::CheckoutError;

pub(super) fn run<I, S>(
    directory: Option<&Path>,
    operation: &'static str,
    arguments: I,
) -> Result<(), CheckoutError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let output = command(directory, arguments)
        .output()
        .map_err(|source| CheckoutError::Io {
            path: directory.unwrap_or_else(|| Path::new("git")).to_path_buf(),
            source,
        })?;
    require_success(operation, output).map(|_| ())
}

pub(super) fn output<I, S>(
    directory: Option<&Path>,
    operation: &'static str,
    arguments: I,
) -> Result<String, CheckoutError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let output = command(directory, arguments)
        .output()
        .map_err(|source| CheckoutError::Io {
            path: directory.unwrap_or_else(|| Path::new("git")).to_path_buf(),
            source,
        })?;
    let output = require_success(operation, output)?;
    String::from_utf8(output.stdout)
        .map(|text| text.trim().to_owned())
        .map_err(|source| CheckoutError::GitOutput { operation, source })
}

fn command<I, S>(directory: Option<&Path>, arguments: I) -> Command
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let mut command = Command::new("git");
    command.args(arguments);
    if let Some(directory) = directory {
        command.current_dir(directory);
    }
    command
}

fn require_success(operation: &'static str, output: Output) -> Result<Output, CheckoutError> {
    if output.status.success() {
        return Ok(output);
    }

    let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
    Err(CheckoutError::Git {
        operation,
        status: output.status,
        stderr,
    })
}

pub(super) fn arguments<const N: usize>(values: [&str; N]) -> [OsString; N] {
    values.map(OsString::from)
}

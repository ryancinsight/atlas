//! Command-line interface for Atlas provider checkout.

use std::env;
use std::ffi::OsString;
use std::path::PathBuf;
use std::process::ExitCode;

use atlas_provider_checkout::{CheckoutConfig, checkout};

const ATLAS_REMOTE: &str = "https://github.com/ryancinsight/atlas.git";
const USAGE: &str = "\
usage: checkout-path-dependencies \
  --manifest <path> --destination <path> --atlas-ref <40-hex-sha> \
  --scratch <path> [--atlas-remote <url>]
";

fn main() -> ExitCode {
    match run(env::args_os().skip(1)) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("checkout-path-dependencies: {error}");
            ExitCode::from(2)
        }
    }
}

fn run(arguments: impl Iterator<Item = OsString>) -> Result<(), String> {
    let arguments: Vec<_> = arguments.collect();
    let config = parse_arguments(&arguments)?;
    let summary = checkout(&config).map_err(|error| error.to_string())?;
    println!(
        "verified {} provider checkout(s) and {} dependency manifest(s): {}",
        summary.providers.len(),
        summary.dependency_manifests,
        summary.providers.join(", ")
    );
    Ok(())
}

fn parse_arguments(arguments: &[OsString]) -> Result<CheckoutConfig, String> {
    let mut manifest = None;
    let mut destination = None;
    let mut atlas_revision = None;
    let mut atlas_remote = None;
    let mut scratch = None;
    let mut index = 0;

    while index < arguments.len() {
        let flag = arguments[index]
            .to_str()
            .ok_or_else(|| format!("argument is not valid UTF-8\n\n{USAGE}"))?;
        let value = arguments
            .get(index + 1)
            .ok_or_else(|| format!("missing value for {flag}\n\n{USAGE}"))?;
        match flag {
            "--manifest" => manifest = Some(PathBuf::from(value)),
            "--destination" => destination = Some(PathBuf::from(value)),
            "--atlas-ref" => atlas_revision = value.to_str().map(str::to_owned),
            "--atlas-remote" => atlas_remote = value.to_str().map(str::to_owned),
            "--scratch" => scratch = Some(PathBuf::from(value)),
            _ => return Err(format!("unknown option {flag:?}\n\n{USAGE}")),
        }
        index += 2;
    }

    Ok(CheckoutConfig {
        manifest: manifest.ok_or_else(|| format!("missing --manifest\n\n{USAGE}"))?,
        destination: destination.ok_or_else(|| format!("missing --destination\n\n{USAGE}"))?,
        atlas_revision: atlas_revision.ok_or_else(|| format!("missing --atlas-ref\n\n{USAGE}"))?,
        atlas_remote: atlas_remote.unwrap_or_else(|| ATLAS_REMOTE.to_owned()),
        scratch: scratch.ok_or_else(|| format!("missing --scratch\n\n{USAGE}"))?,
    })
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;

    #[test]
    fn parses_complete_configuration() {
        let sha = "0123456789abcdef0123456789abcdef01234567";
        let config = parse_arguments(&[
            "--manifest".into(),
            "consumer/Cargo.toml".into(),
            "--destination".into(),
            ".".into(),
            "--atlas-ref".into(),
            sha.into(),
            "--scratch".into(),
            "target/graph".into(),
        ])
        .unwrap();

        assert_eq!(config.manifest, PathBuf::from("consumer/Cargo.toml"));
        assert_eq!(config.destination, PathBuf::from("."));
        assert_eq!(config.atlas_revision, sha);
        assert_eq!(config.atlas_remote, ATLAS_REMOTE);
        assert_eq!(config.scratch, PathBuf::from("target/graph"));
    }

    #[test]
    fn rejects_unknown_option() {
        let error = parse_arguments(&["--branch".into(), "main".into()]).unwrap_err();

        assert!(error.contains("unknown option \"--branch\""));
    }
}

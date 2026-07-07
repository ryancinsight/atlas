//! xtask - Helios Atlas-migration audit gate.
//!
//! Mirrors the cfdrs/kwavers/ritk xtask pattern. Two subcommands:
//!
//! * `cargo run -p xtask -- legacy-migration-audit`
//!     Prints the current legacy-surface scan, then `bail!`s if any new
//!     entry is not already present in `xtask/legacy_surface.allowlist`.
//! * `cargo run -p xtask -- refresh-legacy-allowlist`
//!     Rewrites `xtask/legacy_surface.allowlist` to the current baseline
//!     of legacy-surface manifest + source entries.
//!
//! Atlas context: Helios depends on ritk/gaia/hephaestus/coeus/moirai/etc.
//! The legacy surface (nalgebra/ndarray/burn/tokio/rayon/approx/num_traits/
//! rustfft) is being progressively replaced by these Atlas foundations; this
//! gate catches accidental re-introductions on PRs.

#![allow(clippy::redundant_pattern_matching)]
#![allow(clippy::manual_let_else)]
#![allow(clippy::unnecessary_wraps)]

use anyhow::Result;
use clap::{Parser, Subcommand};
use std::env;
use std::path::{Path, PathBuf};

mod migration_audit;

#[derive(Parser)]
#[command(name = "xtask")]
#[command(about = "Helios Atlas-migration audit gate")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Audit legacy nalgebra/ndarray/burn/tokio/rayon migration surface.
    LegacyMigrationAudit,
    /// Refresh the legacy migration allowlist baseline file.
    RefreshLegacyAllowlist,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::LegacyMigrationAudit => {
            migration_audit::print_legacy_migration_audit(&project_root())
        }
        Commands::RefreshLegacyAllowlist => {
            migration_audit::refresh_legacy_allowlist(&project_root())
        }
    }
}

/// Workspace root ancestor (xtask is at `<root>/xtask/Cargo.toml`).
fn project_root() -> PathBuf {
    Path::new(&env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(1)
        .unwrap()
        .to_path_buf()
}

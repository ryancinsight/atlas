//! Output formatters for the coherence audit.
//!
//! Three formats are supported:
//!  - [`Format::Human`]: compact text readable from a terminal.
//!  - [`Format::Markdown`]: a Markdown table suitable for backlog / PR
//!    snippets.
//!  - [`Format::Json`]: machine-readable JSON via `serde_json`.
//!
//! The formatters are separated from the probe logic so the CLI dispatcher
//! can choose one without changing the audit body. They never invoke git.
//!
//! Determinism contract: the markdown and JSON outputs are stable across
//! runs given the same input `.gitmodules` and probe results — order is
//! preserved from the input table by [`crate::gitmodules::GitmodulesTable`].
//! This is the regression-assertion basis for the snapshot test below.

use serde::Serialize;
use std::fmt::Write as _;

use crate::coherence::{Coherence, DefectClass, RepoProbe};

/// The available output formats.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Format {
    /// Compact, terminal-readable text. Default.
    #[default]
    Human,
    /// A Markdown table.
    Markdown,
    /// A single JSON object containing the full audit.
    Json,
}

impl Format {
    /// Parses a `--format` value to a [`Format`].
    ///
    /// # Errors
    ///
    /// Returns `Err(String)` when the supplied value is not one of `human`,
    /// `markdown`/`md`, or `json`. The string is a human-readable diagnostic
    /// suitable for surfacing in CLI stderr.
    pub fn from_str_value(s: &str) -> Result<Self, String> {
        match s.to_ascii_lowercase().as_str() {
            "human" | "" => Ok(Self::Human),
            "markdown" | "md" => Ok(Self::Markdown),
            "json" => Ok(Self::Json),
            other => Err(format!(
                "unknown --format value `{other}` (expected human|markdown|json)"
            )),
        }
    }
}

/// A summary row for human/markdown rendering.
///
/// Computed once from the full [`Coherence`] result and then rendered into
/// either format — keeps the markdown and human view synchronized.
#[derive(Debug, Clone, Serialize)]
pub struct Report {
    /// Total submodule count probed.
    pub total: usize,
    /// Coherence defect count (categories A/B/C, no-origin-main, unreachable).
    pub defects: usize,
    /// Stale-advanceable count (gitlink behind origin/main but not broken).
    pub stale_advanceable: usize,
    /// Clean count (pin == origin/main or pin ancestral).
    pub clean: usize,
    /// The full probe vector (ordered by `.gitmodules`).
    pub probes: Vec<RepoProbe>,
}

impl From<&Coherence> for Report {
    fn from(c: &Coherence) -> Self {
        let mut defects = 0_usize;
        let mut stale = 0_usize;
        let mut clean = 0_usize;
        for p in &c.probes {
            match p.class {
                DefectClass::Clean => clean += 1,
                DefectClass::StaleAdvanceable => stale += 1,
                _ => defects += 1,
            }
        }
        Self {
            total: c.probes.len(),
            defects,
            stale_advanceable: stale,
            clean,
            probes: c.probes.clone(),
        }
    }
}

impl Report {
    /// Renders the report in the requested format. The returned `String` is
    /// the full content to be written to stdout.
    #[must_use]
    pub fn render(&self, format: Format) -> String {
        match format {
            Format::Human => self.render_human(),
            Format::Markdown => self.render_markdown(),
            Format::Json => self.render_json(),
        }
    }

    fn render_human(&self) -> String {
        let mut out = String::new();
        writeln!(
            out,
            "gitlink-coherence: {} probed | {} defects | {} stale-advanceable | {} clean",
            self.total, self.defects, self.stale_advanceable, self.clean
        )
        .ok();
        if !self.defects() && !self.stale_advanceable() {
            writeln!(out, "(no coherence defects and no stale pins)").ok();
            return out;
        }
        if !self.stale_advanceable() && self.defects > 0 {
            // Skip explicit header
        } else if self.stale_advanceable > 0 {
            writeln!(out, "stale-advanceable (gitlink behind origin/main):").ok();
            for p in self.stale_rows() {
                writeln!(
                    out,
                    "  {}: pin={} origin-main={} — stale",
                    p.submodule.name,
                    short_sha(&p.pin),
                    short_sha(origin_or_empty(p))
                )
                .ok();
            }
        }
        if self.defects > 0 {
            writeln!(out, "defects:").ok();
            for p in self.defect_rows() {
                writeln!(
                    out,
                    "  [{}] {}: pin={} origin-main={} — {}",
                    class_label(&p.class),
                    p.submodule.name,
                    short_sha(&p.pin),
                    short_sha(origin_or_empty(p)),
                    p.note
                )
                .ok();
            }
        }
        out
    }

    fn render_markdown(&self) -> String {
        let mut out = String::new();
        writeln!(out, "| # | submodule | class | pin | origin/main | note |").ok();
        writeln!(out, "|---|-----------|-------|-----|-------------|------|").ok();
        for (idx, p) in self.probes.iter().enumerate() {
            writeln!(
                out,
                "| {} | `{}` | {} | `{}` | `{}` | {} |",
                idx + 1,
                p.submodule.name,
                class_label(&p.class),
                short_sha(&p.pin),
                short_sha(origin_or_empty(p)),
                p.note.replace('|', "\\|"),
            )
            .ok();
        }
        writeln!(
            out,
            "\n**summary:** {} total · {} defects · {} stale · {} clean",
            self.total, self.defects, self.stale_advanceable, self.clean
        )
        .ok();
        out
    }

    fn render_json(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_else(|err| {
            // Only fails on non-serializable types (we control all types
            // here, but cover the contract regardless).
            format!("{{\"error\":\"serde_json failed: {err}\"}}")
        })
    }

    fn defects(&self) -> bool {
        self.defects > 0
    }
    fn stale_advanceable(&self) -> bool {
        self.stale_advanceable > 0
    }
    fn defect_rows(&self) -> impl Iterator<Item = &RepoProbe> {
        self.probes
            .iter()
            .filter(|p| !matches!(p.class, DefectClass::Clean | DefectClass::StaleAdvanceable))
    }
    fn stale_rows(&self) -> impl Iterator<Item = &RepoProbe> {
        self.probes
            .iter()
            .filter(|p| matches!(p.class, DefectClass::StaleAdvanceable))
    }
}

fn origin_or_empty(p: &RepoProbe) -> &str {
    p.origin_main.as_deref().unwrap_or("")
}

/// Shortens a 40-char SHA to the canonical 8-char prefix for tabular viewing.
fn short_sha(sha: &str) -> &str {
    if sha.len() >= 8 { &sha[..8] } else { sha }
}

/// Map a [`DefectClass`] to a stable label suitable for the human/markdown
/// output column.
fn class_label(c: &DefectClass) -> &'static str {
    match c {
        DefectClass::Clean => "clean",
        DefectClass::StaleAdvanceable => "stale",
        DefectClass::NoOriginMainOnRemote => "no-origin-main",
        DefectClass::CategoryA => "cat-a",
        DefectClass::CategoryB => "cat-b",
        DefectClass::CategoryC => "cat-c",
        DefectClass::Unreachable => "unreachable",
        DefectClass::ExecutableUnavailable => "git-missing",
    }
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;
    use crate::gitmodules::Submodule;

    fn mk_probe(name: &str, cls: DefectClass, pin: &str, origin: Option<&str>) -> RepoProbe {
        RepoProbe {
            submodule: Submodule {
                name: name.to_string(),
                path: format!("repos/{name}"),
                url: format!("https://example/{name}"),
            },
            pin: pin.to_string(),
            origin_main: origin.map(std::string::ToString::to_string),
            class: cls,
            note: "n".to_string(),
        }
    }

    #[test]
    fn format_from_str_recognizes_known_inputs() {
        assert_eq!(Format::from_str_value("human").unwrap(), Format::Human);
        assert_eq!(
            Format::from_str_value("MARKDOWN").unwrap(),
            Format::Markdown
        );
        assert_eq!(Format::from_str_value("md").unwrap(), Format::Markdown);
        assert_eq!(Format::from_str_value("json").unwrap(), Format::Json);
        assert_eq!(Format::from_str_value("").unwrap(), Format::Human);
        assert!(Format::from_str_value("xml").is_err());
    }

    #[test]
    fn human_format_summarizes_counts_in_header_line() {
        let c = Coherence {
            probes: vec![
                mk_probe("a", DefectClass::Clean, "1111111", Some("1111111")),
                mk_probe(
                    "b",
                    DefectClass::StaleAdvanceable,
                    "2222222",
                    Some("3333333"),
                ),
                mk_probe("c", DefectClass::CategoryA, "4444444", Some("5555555")),
            ],
        };
        let r = Report::from(&c);
        let human = r.render(Format::Human);
        assert!(
            human.starts_with(
                "gitlink-coherence: 3 probed | 1 defects | 1 stale-advanceable | 1 clean"
            ),
            "header line was: {human}"
        );
        // The defect row should mention "cat-a".
        assert!(human.contains("[cat-a]"), "missing cat-a row: {human}");
    }

    #[test]
    fn markdown_emits_a_table_with_summary() {
        let c = Coherence {
            probes: vec![mk_probe(
                "a",
                DefectClass::Clean,
                "1111111",
                Some("1111111"),
            )],
        };
        let r = Report::from(&c);
        let md = r.render(Format::Markdown);
        assert!(
            md.starts_with("| # | submodule | class | pin | origin/main | note |"),
            "missing table header: {md}"
        );
        assert!(md.contains("**summary:**"));
    }

    #[test]
    fn json_emit_is_serialisable_and_parseable() {
        let c = Coherence {
            probes: vec![mk_probe("a", DefectClass::CategoryB, "1111111", None)],
        };
        let r = Report::from(&c);
        let json = r.render(Format::Json);
        assert!(
            json.contains("\"defects\": 1"),
            "missing defects count: {json}"
        );
        // Round-trip parse to ensure structure is JSON.
        serde_json::from_str::<serde_json::Value>(&json).expect("parseable JSON");
    }

    #[test]
    fn class_labels_stable_for_snapshot() {
        // Pin the label strings for the regression-snapshot contract.
        assert_eq!(class_label(&DefectClass::Clean), "clean");
        assert_eq!(class_label(&DefectClass::StaleAdvanceable), "stale");
        assert_eq!(class_label(&DefectClass::CategoryA), "cat-a");
        assert_eq!(class_label(&DefectClass::CategoryB), "cat-b");
        assert_eq!(class_label(&DefectClass::CategoryC), "cat-c");
        assert_eq!(
            class_label(&DefectClass::NoOriginMainOnRemote),
            "no-origin-main"
        );
        assert_eq!(class_label(&DefectClass::Unreachable), "unreachable");
        assert_eq!(
            class_label(&DefectClass::ExecutableUnavailable),
            "git-missing"
        );
    }
}

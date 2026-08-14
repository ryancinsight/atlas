//! Report rendering for the manifest-version guard findings.
//!
//! Two formats:
//! - [`Format::Human`] — one finding per line, classified by direction; the
//!   exit-code-bearing binary prints this to stdout. A trailing summary is
//!   emitted when findings are non-empty.
//! - [`Format::Json`] — a JSON object `{"defect_count": N, "findings": [...]}`.
//!
//! The JSON serde surface mirrors `tools/gitlink-coherence/src/report.rs`:
//! findings serialize as a typed object so a future CI consumer can consume
//! the report programmatically.

use crate::classify::IntentDeclaration;
use crate::scan::{Finding, has_defect};
use serde::Serialize;

/// Output format for the report: human- or machine-readable JSON.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Format {
    /// Human-readable, one finding per line.
    Human,
    /// Machine-readable JSON.
    Json,
}

impl Format {
    /// Parse a `--format` argument value. Returns `None` for an
    /// unrecognised value so the caller can emit a typed error.
    #[must_use]
    pub fn from_str_value(value: &str) -> Option<Self> {
        match value {
            "human" => Some(Self::Human),
            "json" => Some(Self::Json),
            _ => None,
        }
    }
}

/// Serializable view of a single finding, used by the JSON formatter.
#[derive(Debug, Serialize)]
struct FindingView<'a> {
    path: &'a str,
    line_no: u32,
    direction: &'static str,
    intent: &'static str,
    message: &'a str,
}

/// A rendered-ready report.
#[derive(Debug)]
pub struct Report<'a> {
    findings: &'a [Finding],
    intent: IntentDeclaration,
}

impl<'a> Report<'a> {
    /// Construct a report view over a borrowed findings slice.
    #[must_use]
    pub const fn new(findings: &'a [Finding], intent: IntentDeclaration) -> Self {
        Self { findings, intent }
    }

    /// Render the report in the given format.
    #[must_use]
    pub fn render(&self, format: Format) -> String {
        match format {
            Format::Human => self.render_human(),
            Format::Json => self.render_json(),
        }
    }

    fn render_human(&self) -> String {
        let mut out = String::new();
        if self.findings.is_empty() {
            out.push_str("version-guard: no version-bearing lines touched\n");
        } else {
            for f in self.findings {
                out.push_str(&f.message);
                out.push('\n');
            }
        }
        if has_defect(self.findings, self.intent) {
            out.push_str("version-guard: DEFECT\n");
        } else {
            out.push_str("version-guard: clean\n");
        }
        out
    }

    fn render_json(&self) -> String {
        // Declared before the statements that use it: items are in scope for
        // the whole block regardless of position, so placing this mid-body
        // only misleads the reader about when it takes effect.
        #[derive(Serialize)]
        struct ReportView<'a> {
            defect_count: usize,
            findings: Vec<FindingView<'a>>,
        }

        let views: Vec<FindingView<'_>> = self
            .findings
            .iter()
            .map(|f| FindingView {
                path: &f.path,
                line_no: f.line_no,
                direction: direction_str(f.direction),
                intent: intent_str(f.intent),
                message: &f.message,
            })
            .collect();
        let finding_defects = self
            .findings
            .iter()
            .filter(|finding| {
                matches!(
                    finding.direction,
                    crate::classify::Direction::Backward | crate::classify::Direction::Forward
                ) && (finding.direction == crate::classify::Direction::Backward
                    || self.intent == IntentDeclaration::Undeclared)
            })
            .count();
        let defect_count = if has_defect(self.findings, self.intent) {
            finding_defects.max(1)
        } else {
            0
        };
        let view = ReportView {
            defect_count,
            findings: views,
        };
        serde_json::to_string(&view)
            .unwrap_or_else(|_| String::from("{\"error\": \"serialization failed\"}"))
    }
}

/// Render the report in the given format. Library entry point for callers
/// that hold a findings slice directly (no `Report` indirection).
#[must_use]
pub fn render(findings: &[Finding], intent: IntentDeclaration, format: Format) -> String {
    Report::new(findings, intent).render(format)
}

fn direction_str(direction: crate::classify::Direction) -> &'static str {
    use crate::classify::Direction;
    match direction {
        Direction::Identical => "identical",
        Direction::Forward => "forward",
        Direction::Backward => "backward",
    }
}

fn intent_str(intent: crate::classify::IntentDeclaration) -> &'static str {
    use crate::classify::IntentDeclaration;
    match intent {
        IntentDeclaration::Declared => "declared",
        IntentDeclaration::Undeclared => "undeclared",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::classify::{Direction, IntentDeclaration};
    use crate::parse::LineKind;
    use crate::scan::Finding;

    fn sample_finding(direction: Direction, intent: IntentDeclaration) -> Finding {
        Finding {
            path: "Cargo.toml".to_string(),
            line_no: 5,
            kind: LineKind::Version,
            direction,
            intent,
            message: format!(
                "Cargo.toml:5 version \"0.5.0\" -> \"0.4.1\" ({})",
                match direction {
                    Direction::Backward => "BACKWARD",
                    Direction::Forward => "forward (UNDECLARED)",
                    Direction::Identical => "identical",
                }
            ),
        }
    }

    #[test]
    fn empty_findings_human_format_reports_clean_without_intent() {
        let r = render(&[], IntentDeclaration::Undeclared, Format::Human);
        assert!(r.contains("no version-bearing lines"));
    }

    #[test]
    fn declared_intent_empty_findings_human_format_reports_defect() {
        let r = render(&[], IntentDeclaration::Declared, Format::Human);
        assert!(r.contains("no version-bearing lines"));
        assert!(r.contains("DEFECT"));
    }

    #[test]
    fn backward_finding_human_format_reports_defect() {
        let f = sample_finding(Direction::Backward, IntentDeclaration::Undeclared);
        let r = render(&[f], IntentDeclaration::Undeclared, Format::Human);
        assert!(r.contains("BACKWARD"));
        assert!(r.contains("DEFECT"));
    }

    #[test]
    fn identical_finding_human_format_reports_clean() {
        let f = sample_finding(Direction::Identical, IntentDeclaration::Undeclared);
        let r = render(&[f], IntentDeclaration::Undeclared, Format::Human);
        assert!(r.contains("identical"));
        assert!(r.contains("clean"));
        assert!(!r.contains("DEFECT"));
    }

    #[test]
    fn json_format_emits_valid_json() {
        let f = sample_finding(Direction::Backward, IntentDeclaration::Undeclared);
        let r = render(&[f], IntentDeclaration::Undeclared, Format::Json);
        let parsed: serde_json::Value = serde_json::from_str(&r).expect("valid JSON");
        assert_eq!(parsed["defect_count"], 1);
        assert_eq!(parsed["findings"][0]["direction"], "backward");
    }

    #[test]
    fn json_format_reports_missing_declared_movement() {
        let r = render(&[], IntentDeclaration::Declared, Format::Json);
        let parsed: serde_json::Value = serde_json::from_str(&r).expect("valid JSON");
        assert_eq!(parsed["defect_count"], 1);
        assert!(parsed["findings"].as_array().is_some_and(Vec::is_empty));
    }

    #[test]
    fn format_from_str_recognises_human_and_json() {
        assert_eq!(Format::from_str_value("human"), Some(Format::Human));
        assert_eq!(Format::from_str_value("json"), Some(Format::Json));
        assert_eq!(Format::from_str_value("yaml"), None);
    }
}

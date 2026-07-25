//! Parser for `.gitmodules`.
//!
//! The atlas-meta `.gitmodules` file uses git's INI-style submodule format:
//!
//! ```text
//! [submodule "repos/coeus"]
//!     path = repos/coeus
//!     url = https://github.com/ryancinsight/coeus
//!     active = true
//! ```
//!
//! This module provides a small, dependency-free parser that yields the
//! canonical `(<name>, <path>, <url>)` triples. The `active` flag is not
//! surfaced: the audit probes every registered submodule unconditionally, and
//! an inactive submodule whose gitlink drifted is a coherence defect that the
//! tool should still catch.

use std::fmt;
use std::str::FromStr;

/// A single `.gitmodules` submodule entry.
///
/// The canonical form keeps all three fields together so the auditor can
/// resolve the local gitlink onto a single home directory, the member-repo
/// origin URL, and a stable name for reporting. Lifetime-free by design: the
/// parsed result is small (≈25 entries × ≈80 bytes) and lives for the
/// duration of one audit pass.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct Submodule {
    /// The name as written inside the `[submodule "<name>"]` header. Atlas
    /// convention prefixes with `repos/` so the name matches the submodule
    /// path verbatim.
    pub name: String,
    /// The relative filesystem path under atlas-meta where the submodule is
    /// checked out (e.g. `repos/coeus`).
    pub path: String,
    /// The configured upstream URL (e.g.
    /// `https://github.com/ryancinsight/coeus`). Used for diagnostic context
    /// in the report formatters; not invoked directly by the auditor (the
    /// auditor reads from the locally-checked-out `repos/<R>/.git` so it
    /// never makes outbound network requests).
    pub url: String,
}

impl fmt::Display for Submodule {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} @ {} <- {}", self.name, self.path, self.url)
    }
}

/// Errors from parsing `.gitmodules`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseError {
    /// A `<key> = <value>` line appeared outside any section header.
    OrphanAssignment(String),
    /// A `[submodule "<name>"]` header was malformed.
    MalformedHeader(String),
    /// A section opened with a type other than `submodule`.
    UnexpectedSection(String),
    /// A submodule section was missing the `path = ...` assignment.
    MissingPath(String),
    /// A submodule section was missing the `url = ...` assignment.
    MissingUrl(String),
}

impl ParseError {
    fn orphan_assignment(line: impl Into<String>) -> Self {
        Self::OrphanAssignment(line.into())
    }
    fn malformed_header(line: impl Into<String>) -> Self {
        Self::MalformedHeader(line.into())
    }
    fn unexpected_section(line: impl Into<String>) -> Self {
        Self::UnexpectedSection(line.into())
    }
    fn missing_path(name: impl Into<String>) -> Self {
        Self::MissingPath(name.into())
    }
    fn missing_url(name: impl Into<String>) -> Self {
        Self::MissingUrl(name.into())
    }
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::OrphanAssignment(line) => {
                write!(f, "orphan assignment outside section header: `{line}`")
            }
            Self::MalformedHeader(line) => {
                write!(f, "malformed submodule header: `{line}`")
            }
            Self::UnexpectedSection(line) => {
                write!(f, "unexpected non-submodule section: `{line}`")
            }
            Self::MissingPath(name) => {
                write!(f, "submodule `{name}` has no `path = ...` assignment")
            }
            Self::MissingUrl(name) => {
                write!(f, "submodule `{name}` has no `url = ...` assignment")
            }
        }
    }
}

impl std::error::Error for ParseError {}

/// Parsed `.gitmodules` table.
///
/// The table preserves insertion order so audit output is deterministic from
/// one run to the next (determinism is required by the regression-test
/// snapshot in [`crate::report`]).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GitmodulesTable {
    /// Submodules in file order.
    pub submodules: Vec<Submodule>,
}

impl GitmodulesTable {
    /// Look up a submodule by its bare name (e.g. `coeus` matches
    /// `repos/coeus`). Returns `None` if the bare name is not a unique
    /// submodule match.
    #[must_use]
    pub fn find_by_bare_name(&self, bare: &str) -> Option<&Submodule> {
        // Atlas convention: the section name is the full path,
        // so the bare name is the final path component.
        self.submodules
            .iter()
            .find(|s| s.name == bare || s.name.ends_with(&format!("/{bare}")) || s.path == bare)
    }
}

impl FromStr for GitmodulesTable {
    type Err = ParseError;

    fn from_str(input: &str) -> Result<Self, Self::Err> {
        let mut submodules = Vec::new();
        let mut current_header: Option<String> = None;
        let mut current_path: Option<String> = None;
        let mut current_url: Option<String> = None;

        for raw in input.lines() {
            let line = raw.trim();
            if line.is_empty() || line.starts_with('#') || line.starts_with(';') {
                continue;
            }
            if line.starts_with('[') && line.ends_with(']') {
                // Flush any in-progress section that declared a submodule
                // header but did not yet see both required keys.
                if let Some(name) = current_header.take() {
                    let path = current_path
                        .take()
                        .ok_or_else(|| ParseError::missing_path(name.clone()))?;
                    let url = current_url
                        .take()
                        .ok_or_else(|| ParseError::missing_url(name.clone()))?;
                    submodules.push(Submodule { name, path, url });
                }
                current_path = None;
                current_url = None;

                // Parse the new header.
                let inner = &line[1..line.len() - 1];
                let (section_type, opt_quoted_name) = match inner.split_once(' ') {
                    Some((t, rest)) => (t.trim(), Some(rest.trim())),
                    None => (inner.trim(), None),
                };
                if section_type != "submodule" {
                    return Err(ParseError::unexpected_section(line.to_string()));
                }
                let name = match opt_quoted_name {
                    Some(q) => {
                        let q = q.trim();
                        if q.len() < 2 || !q.starts_with('"') || !q.ends_with('"') {
                            return Err(ParseError::malformed_header(line.to_string()));
                        }
                        q[1..q.len() - 1].to_string()
                    }
                    None => return Err(ParseError::malformed_header(line.to_string())),
                };
                current_header = Some(name);
                continue;
            }
            if let Some((key, value)) = line.split_once('=') {
                let key = key.trim();
                let value = value.trim().to_string();
                if current_header.is_none() {
                    return Err(ParseError::orphan_assignment(line.to_string()));
                }
                match key {
                    "path" => current_path = Some(value),
                    "url" => current_url = Some(value),
                    _ => {
                        // Unknown keys (e.g. `active`) are ignored — see the
                        // module docs.
                    }
                }
                continue;
            }
            return Err(ParseError::malformed_header(line.to_string()));
        }

        if let Some(name) = current_header.take() {
            let path = current_path
                .take()
                .ok_or_else(|| ParseError::missing_path(name.clone()))?;
            let url = current_url
                .take()
                .ok_or_else(|| ParseError::missing_url(name.clone()))?;
            submodules.push(Submodule { name, path, url });
        }
        Ok(Self { submodules })
    }
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used)]

    use super::*;

    #[test]
    fn parse_minimal_submodule() {
        let input = "[submodule \"repos/coeus\"]\n    path = repos/coeus\n    url = https://github.com/ryancinsight/coeus\n    active = true\n";
        let table: GitmodulesTable = input.parse().unwrap();
        assert_eq!(table.submodules.len(), 1);
        let s = &table.submodules[0];
        assert_eq!(s.name, "repos/coeus");
        assert_eq!(s.path, "repos/coeus");
        assert_eq!(s.url, "https://github.com/ryancinsight/coeus");
    }

    #[test]
    fn parse_multiple_submodules_preserves_order() {
        let input = "[submodule \"repos/apollo\"]\n    path = repos/apollo\n    url = https://github.com/ryancinsight/apollo\n\n[submodule \"repos/athena\"]\n    path = repos/athena\n    url = https://github.com/ryancinsight/athena\n";
        let table: GitmodulesTable = input.parse().unwrap();
        assert_eq!(table.submodules.len(), 2);
        assert_eq!(table.submodules[0].name, "repos/apollo");
        assert_eq!(table.submodules[1].name, "repos/athena");
    }

    #[test]
    fn parse_round_trip_with_blank_and_comment_lines() {
        let input = "# atlas meta-repo submodules\n\n[submodule \"repos/coeus\"]\n    path = repos/coeus\n    url = https://github.com/ryancinsight/coeus\n    ; inline comment handled by trim\n    active = true\n\n; one more after\n";
        let table: GitmodulesTable = input.parse().unwrap();
        assert_eq!(table.submodules.len(), 1);
        assert_eq!(table.submodules[0].name, "repos/coeus");
    }

    #[test]
    fn parse_rejects_non_submodule_section() {
        let input = "[not_submodule \"foo\"]\n    path = repos/coeus\n    url = https://github.com/ryancinsight/coeus\n";
        let err: ParseError = input.parse::<GitmodulesTable>().unwrap_err();
        assert_eq!(
            err,
            ParseError::UnexpectedSection("[not_submodule \"foo\"]".to_string())
        );
    }

    #[test]
    fn parse_rejects_missing_path() {
        let input =
            "[submodule \"repos/coeus\"]\n    url = https://github.com/ryancinsight/coeus\n";
        let err: ParseError = input.parse::<GitmodulesTable>().unwrap_err();
        assert_eq!(err, ParseError::MissingPath("repos/coeus".to_string()));
    }

    #[test]
    fn parse_rejects_missing_url() {
        let input = "[submodule \"repos/coeus\"]\n    path = repos/coeus\n";
        let err: ParseError = input.parse::<GitmodulesTable>().unwrap_err();
        assert_eq!(err, ParseError::MissingUrl("repos/coeus".to_string()));
    }

    #[test]
    fn parse_rejects_orphan_assignment() {
        let input = "path = repos/coeus\n";
        let err: ParseError = input.parse::<GitmodulesTable>().unwrap_err();
        assert!(matches!(err, ParseError::OrphanAssignment(_)));
    }

    #[test]
    fn parse_rejects_malformed_header() {
        let input = "[submodule repos/coeus]\n    path = repos/coeus\n    url = https://github.com/ryancinsight/coeus\n";
        let err: ParseError = input.parse::<GitmodulesTable>().unwrap_err();
        assert!(matches!(err, ParseError::MalformedHeader(_)));
    }

    #[test]
    fn find_by_bare_name_matches_substring_suffix() {
        let input = "[submodule \"repos/coeus\"]\n    path = repos/coeus\n    url = https://github.com/ryancinsight/coeus\n";
        let table: GitmodulesTable = input.parse().unwrap();
        let s = table.find_by_bare_name("coeus").expect("found");
        assert_eq!(s.path, "repos/coeus");
        assert!(table.find_by_bare_name("missing").is_none());
    }
}

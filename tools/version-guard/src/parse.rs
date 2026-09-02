//! Parsing of `*.toml` unified diff lines into version-bearing entries.
//!
//! The parser is intentionally narrow: it matches `version = "X.Y.Z"` lines
//! only — the three surfaces identically named in the
//! `[workspace.package].version`, `[package].version`, and inline-table dep
//! forms `dep = { version = "X.Y.Z", ... }`. The diff line carries a leading
//! `+`, `-`, optional space, and the content after the optional `+`/`-`
//! marker; the surrounding TOML heading lives in the file pre-image and is
//! not visible in a unified-diff line, so the kind (workspace / package / dep)
//! is recorded as the broader `LineKind::Version` and refined in a later
//! sub-delivery when the heading-tracking surface lands.
//!
//! Semver parsing recognises `MAJOR.MINOR.PATCH` and optional pre-release /
//! build metadata per <https://semver.org>. Pre-release sorts before the
//! release it modifies; build metadata is ignored for ordering. The
//! implementation is dependency-free and handles only the cases Atlas member
//! manifests actually emit — full SemVer regex compliance is out of scope
//! for the skeleton.

use std::cmp::Ordering;

/// Kind of version-bearing TOML line encountered in the diff.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LineKind {
    /// A `version = "X.Y.Z"` line. The skeleton does not yet discriminate
    /// between `[workspace.package].version`, `[package].version`, and
    /// inline-table `dep = { version = "X.Y.Z", ... }` — all three carry the
    /// identical line shape and are flagged identically. A later sub-delivery
    /// parses surrounding context to refine the kind.
    Version,
}

/// One version-bearing line parsed out of a unified diff.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VersionLine {
    /// Path of the source file, captured from the `diff --git` header.
    pub path: String,
    /// 1-based line number within the post-image file (from the `@@` hunk
    /// header). Used to pair `+`/`-` lines of the same logical version
    /// field when both sides are present.
    pub line_no: u32,
    /// The version string captured from the line, without quotes.
    pub version: String,
    /// Whether this is an addition (`+`) or deletion (`-`).
    pub side: DiffSide,
    /// Which kind of version line this is.
    pub kind: LineKind,
}

/// Which side of a diff a line belongs to.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DiffSide {
    /// An added line (`+`).
    Added,
    /// A removed line (`-`).
    Removed,
}

/// Parse a semver string into a triple of `(major, minor, patch, pre_release)`
/// for ordering. Returns `None` if the input does not match
/// `MAJOR.MINOR.PATCH` optionally followed by `-<pre>` / `+<build>`.
///
/// Build metadata (`+<build>`) is stripped before comparison per `SemVer`
/// §10 ("Build metadata MUST be ignored when determining version
/// precedence"). Pre-release (`-<pre>`) is retained and orders before the
/// release it modifies; a release with no pre-release orders after one
/// with a pre-release at the same `MAJOR.MINOR.PATCH`.
fn parse_semver_triple(s: &str) -> Option<(u64, u64, u64, Option<String>)> {
    // Strip build metadata (`+...`) — ignored for ordering.
    let s = s.split('+').next().unwrap_or(s);
    // Split off pre-release (`-...`) — retained.
    let (core, pre) = match s.split_once('-') {
        Some((c, p)) => (c, Some(p.to_string())),
        None => (s, None),
    };
    let mut parts = core.split('.');
    let major = parts.next()?.parse::<u64>().ok()?;
    let minor = parts.next()?.parse::<u64>().ok()?;
    let patch = parts.next()?.parse::<u64>().ok()?;
    if parts.next().is_some() {
        return None;
    }
    Some((major, minor, patch, pre))
}

/// Parse a semver string into an ordering key. Returns `None` on parse
/// failure. Two equal keys compare equal; pre-release sorts before the
/// release at the same triple.
///
/// This is the public entry used by [`crate::classify::classify_pair`].
#[must_use]
pub fn parse_semver(s: &str) -> Option<SemVerKey> {
    let (major, minor, patch, pre) = parse_semver_triple(s)?;
    Some(SemVerKey {
        major,
        minor,
        patch,
        pre,
    })
}

/// Ordering key for a parsed semver. Two equivalent versions produce equal
/// keys; pre-release ordering is encoded so a release with a pre-release
/// sorts strictly before the same triple without one.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SemVerKey {
    major: u64,
    minor: u64,
    patch: u64,
    pre: Option<String>,
}

impl Ord for SemVerKey {
    fn cmp(&self, other: &Self) -> Ordering {
        self.major
            .cmp(&other.major)
            .then_with(|| self.minor.cmp(&other.minor))
            .then_with(|| self.patch.cmp(&other.patch))
            .then_with(|| match (&self.pre, &other.pre) {
                (None, None) => Ordering::Equal,
                // A release with no pre-release > a release with pre-release.
                (None, Some(_)) => Ordering::Greater,
                (Some(_), None) => Ordering::Less,
                (Some(a), Some(b)) => a.cmp(b),
            })
    }
}

impl PartialOrd for SemVerKey {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// Return the byte offset of a TOML `version` key in `rest`, or `None`.
///
/// The key must stand alone as a TOML key, not appear as a suffix of a
/// longer key. A bare `version` key may be preceded by the start of the
/// line, whitespace, or an inline-table delimiter (`{` or `,`); the same
/// delimiter test excludes `rust-version` and `package_version` while
/// accepting `dep = { version = "..." }`. Because `rest` has already been
/// trimmed, a leading key sits at offset 0.
fn find_version_key(rest: &str) -> Option<usize> {
    let mut search_from = 0;
    while let Some(idx) = rest[search_from..].find("version") {
        let start = search_from + idx;
        let end = start + "version".len();
        // The key must not be the tail of a longer identifier: the char
        // before `version` must not be an identifier byte (ASCII letter,
        // digit, `_`, or `-`). The line start, whitespace, and the inline-
        // table delimiters `{` / `,` all pass; `rust-version` and
        // `package_version` fail.
        let preceded = rest[..start].chars().next_back();
        let prefix_ok = match preceded {
            None => true,
            Some(c) => !c.is_ascii_alphanumeric() && c != '_' && c != '-',
        };
        // The char(s) after the key must open the `= "..."` value. A key
        // that is a prefix of a longer one (e.g. `version_x`) is rejected
        // by requiring the following char to be `=` (after optional spaces).
        let tail = &rest[end..];
        let after_ws = tail.trim_start();
        let followed_by_eq = after_ws.starts_with('=');
        if prefix_ok && followed_by_eq {
            return Some(start);
        }
        search_from = end;
    }
    None
}

/// Parse a single unified-diff line into a [`VersionLine`] if it carries a
/// `version = "X.Y.Z"` entry. Returns `None` for any line that does not
/// match that pattern.
///
/// Recognised shapes:
/// - `+version = "0.5.0"` (addition, workspace or package surface).
/// - `-version = "0.4.1"` (deletion, workspace or package surface).
/// - `+    version = "0.5.0"` (with leading indentation, common inside
///   inline-table dep entries).
///
/// The path and line-number context is supplied by the caller in
/// [`crate::scan::scan_diff`] — this parser does not track file/hunk state.
#[must_use]
pub fn parse_diff_line(line: &str, path: &str, line_no: u32) -> Option<VersionLine> {
    // Determine the diff side and the remainder by stripping the optional
    // `+`/`-` prefix; if neither match, this is a context line or hunk
    // header and not version-bearing.
    let (side, rest) = if let Some(tail) = line.strip_prefix('+') {
        (DiffSide::Added, tail)
    } else {
        let tail = line.strip_prefix('-')?;
        (DiffSide::Removed, tail)
    };
    // Skip the optional leading space introduced by the diff marker, and
    // any further indentation that lives in the file. Trim the trailing
    // newline-equivalent / whitespace so suffix checks succeed.
    let rest = rest.trim();
    // Recognise the TOML `version = "<x>"` shape in two positions:
    //  1. at the start of the trimmed line:
    //        `version = "0.5.0"`
    //     (workspace / package surface — `[workspace.package].version`,
    //     `[package].version`).
    //  2. embedded inside an inline-table dep entry:
    //        `hermes-simd-core = { path = "...", version = "0.5.0" }`
    //     — the motivating `87ab265` hermes incident reverted internal
    //     requirements inside precisely this form.
    //
    // We anchor on the `version` key so both shapes match with one scan:
    //   * bare `version = "..."` (workspace / package surface), and
    //   * `dep = { ..., version = "..." }` (inline-table dep entry).
    //
    // The key must be the whole TOML key, not a suffix of a longer one.
    // `rust-version = "..."` (a different TOML field) and a dep key like
    // `package_version` both contain `version` as a substring, but neither
    // is a package-version declaration; treating either as one extracts a
    // non-semver value from `rust-version` (e.g. `"1.95"`) that classifies
    // as Backward and raises a false defect. A lone `version` key is
    // preceded by nothing, whitespace, or `{` / `,` (inside an inline
    // table), and followed by `=`. After the key, expect optional
    // whitespace, `=`, optional whitespace, then a quoted TOML basic
    // string. We extract the content between the first `\"` and the next
    // `\"` rather than relying on `strip_suffix` — the inline-table form
    // ends in `}`, and the bare `[package].version = "..."` form ends in
    // `\"`, so suffix-matching against the line end fails on the former.
    let version_key = find_version_key(rest)?;
    let after_key = &rest[version_key + "version".len()..];
    let after_eq = after_key.trim_start().strip_prefix('=')?.trim_start();
    let after_open = after_eq.strip_prefix('"')?;
    // Split on the next `\"` to extract the basic-string content.
    let close = after_open.find('"')?;
    let version = &after_open[..close];
    if version.is_empty() {
        return None;
    }
    Some(VersionLine {
        path: path.to_string(),
        line_no,
        version: version.to_string(),
        side,
        kind: LineKind::Version,
    })
}

#[cfg(test)]
#[expect(
    clippy::unwrap_used,
    reason = "test fixtures are known-good; a None here is a broken test, and panicking names it immediately"
)]
mod tests {
    use super::*;

    #[test]
    fn parses_added_workspace_version_line() {
        let v = parse_diff_line(r#"+version = "0.5.0""#, "Cargo.toml", 5).unwrap();
        assert_eq!(v.path, "Cargo.toml");
        assert_eq!(v.line_no, 5);
        assert_eq!(v.version, "0.5.0");
        assert_eq!(v.side, DiffSide::Added);
        assert_eq!(v.kind, LineKind::Version);
    }

    #[test]
    fn parses_removed_version_line() {
        let v = parse_diff_line(r#"-version = "0.4.1""#, "Cargo.toml", 5).unwrap();
        assert_eq!(v.version, "0.4.1");
        assert_eq!(v.side, DiffSide::Removed);
    }

    #[test]
    fn parses_indented_version_line_inside_inline_table() {
        let v = parse_diff_line(r#"+    version = "0.5.0""#, "crates/foo/Cargo.toml", 12).unwrap();
        assert_eq!(v.version, "0.5.0");
        assert_eq!(v.path, "crates/foo/Cargo.toml");
    }

    #[test]
    fn ignores_hunk_header_line() {
        assert!(parse_diff_line("@@ -3,1 +4,1 @@", "Cargo.toml", 4).is_none());
    }

    #[test]
    fn ignores_context_line() {
        assert!(parse_diff_line(r#" version = "0.5.0""#, "Cargo.toml", 5).is_none());
    }

    #[test]
    fn ignores_non_version_key() {
        assert!(parse_diff_line(r#"+name = "atlas""#, "Cargo.toml", 1).is_none());
    }

    #[test]
    fn parses_inline_table_dep_version_entry() {
        // The motivating hermes 87ab265 form: an inline-table dep entry
        // carrying the version requirement after a path/git field.
        let v = parse_diff_line(
            r#"+hermes-simd-core = { path = "../hermes-simd-core", version = "0.4.0" }"#,
            "crates/hermes-simd/Cargo.toml",
            17,
        )
        .unwrap();
        assert_eq!(v.version, "0.4.0");
        assert_eq!(v.path, "crates/hermes-simd/Cargo.toml");
        assert_eq!(v.side, DiffSide::Added);
    }

    #[test]
    fn ignores_inline_table_dep_entry_without_version_key() {
        // An inline-table without a `version =` key (e.g. a clap-like
        // dep that uses only a path-or-version shorthand) must not be
        // mistaken for one.
        assert!(
            parse_diff_line(r#"+leto-ops = { path = "../leto-ops" }"#, "Cargo.toml", 7,).is_none()
        );
    }

    #[test]
    fn ignores_rust_version_field() {
        // `rust-version` is a distinct Cargo field, not a package version.
        // Its value ("1.95") is not SemVer, so matching it would classify a
        // rust-version bump as a Backward package-version defect.
        assert!(parse_diff_line(r#"+rust-version = "1.95""#, "Cargo.toml", 1).is_none());
    }

    #[test]
    fn ignores_package_version_suffixed_key() {
        // A dep key that merely contains `version` as a suffix must not be
        // captured as a version-bearing line.
        assert!(parse_diff_line(r#"+package_version = "0.1.0""#, "Cargo.toml", 1).is_none());
    }

    #[test]
    fn parses_version_key_after_inline_table_delimiter() {
        // The inline-table form after a comma delimiter — `dep = { path = "...",
        // version = "0.4.0" }` — must match, since `version` follows `, `.
        let v = parse_diff_line(
            r#"+hermes-simd = { path = "../x", version = "0.4.0" }"#,
            "Cargo.toml",
            9,
        )
        .unwrap();
        assert_eq!(v.version, "0.4.0");
        assert_eq!(v.side, DiffSide::Added);
    }

    #[test]
    fn ignores_rust_version_suffix_in_inline_key() {
        // A key named `metadata_rust-version` inside an inline table should
        // not be captured; the delimiter is `{` before the key but the key
        // itself still contains `version` only as a suffix.
        assert!(
            parse_diff_line(
                r#"+foo = { metadata_rust-version = "1.95" }"#,
                "Cargo.toml",
                3
            )
            .is_none()
        );
    }

    #[test]
    fn ignores_empty_version_string() {
        assert!(parse_diff_line(r#"+version = """#, "Cargo.toml", 1).is_none());
    }

    #[test]
    fn semver_orders_forward_minor() {
        let a = parse_semver("0.5.0").unwrap();
        let b = parse_semver("0.6.0").unwrap();
        assert!(b > a);
        assert!(a < b);
    }

    #[test]
    fn semver_orders_equal() {
        let a = parse_semver("0.5.0").unwrap();
        let b = parse_semver("0.5.0").unwrap();
        assert_eq!(a.cmp(&b), Ordering::Equal);
    }

    #[test]
    fn semver_orders_backward_patch() {
        let a = parse_semver("0.5.1").unwrap();
        let b = parse_semver("0.5.0").unwrap();
        assert!(b < a);
    }

    #[test]
    fn semver_strips_build_metadata_for_comparison() {
        let a = parse_semver("0.5.0+build.1").unwrap();
        let b = parse_semver("0.5.0+build.2").unwrap();
        assert_eq!(a.cmp(&b), Ordering::Equal);
    }

    #[test]
    fn semver_with_pre_release_orders_before_release() {
        let pre = parse_semver("0.5.0-beta.1").unwrap();
        let release = parse_semver("0.5.0").unwrap();
        assert!(pre < release);
    }

    #[test]
    fn semver_rejects_non_numeric() {
        assert!(parse_semver("not-a-version").is_none());
    }

    #[test]
    fn semver_rejects_too_few_segments() {
        assert!(parse_semver("0.5").is_none());
    }

    #[test]
    fn semver_rejects_too_many_segments() {
        assert!(parse_semver("0.5.0.1").is_none());
    }
}

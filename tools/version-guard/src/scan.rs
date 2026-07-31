//! End-to-end scan of a `*.toml` unified diff into findings.
//!
//! [`scan_diff`] is the library entry point invoked by the binary and by any
//! future meta-level sweep wiring. It accepts the raw diff text and the
//! commit message of the change, splits it on `diff --git` headers, tracks
//! the hunk line numbers, and pairs `+`/`-` `version =` lines for each
//! file by **ordered position** within the file (the `i`-th removal
//! matches the `i`-th addition; see [`scan_diff`] for the rationale).
//! Each pair is classified as [`Direction::Identical`] /
//! [`Direction::Forward`] / [`Direction::Backward`], and the commit
//! message is checked for declared intent per
//! [`crate::classify::classify_intent`].

use crate::classify::{Direction, IntentDeclaration, classify_intent, classify_pair};
use crate::parse::{DiffSide, LineKind, VersionLine, parse_diff_line};

/// One direction-classified finding produced by [`scan_diff`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Finding {
    /// Path of the `*.toml` file owning the version line.
    pub path: String,
    /// 1-based line number of the line in the post-image file.
    pub line_no: u32,
    /// Kind of version line (currently always [`LineKind::Version`]).
    pub kind: LineKind,
    /// Direction of the version movement between the pre-image and
    /// post-image of the file at `(path, line_no)`.
    pub direction: Direction,
    /// Whether the commit message declared release/bump intent.
    pub intent: IntentDeclaration,
    /// Human-readable summary of the finding, suitable for the default
    /// human-format report.
    pub message: String,
}

/// Scan a `*.toml` unified diff and its commit message into a list of
/// classified findings.
///
/// `diff_text` is the raw text of `git diff <range> -- '*.toml'` (or the
/// equivalent manually-produced diff). `commit_msg` is the body of the
/// commit under audit; intent is classified once per call, not once per
/// finding, since the declaration surface is per-commit not per-line.
///
/// Returns the list of findings, possibly empty. An empty list means the
/// diff contained no recognised version-bearing lines (i.e. no `version =`
/// lines were touched at all); the binary's exit code decides whether the
/// change is clean in that case.
///
/// # Pairing semantics
///
/// In a unified diff, removal lines and addition lines are typically
/// blocked together for a single hunk (`-`s first, then `+`s), not
/// interleaved. The standard post-image line counter advances only on
/// `+` and context lines, which makes the post-image coordinate of every
/// removal in a block identical. Rather than try to disambiguate that
/// collision at the coordinate level, we pair by **ordered position**
/// within the file: the `i`-th removal of a file pairs with the `i`-th
/// addition of the same file. This is the right semantic for unified
/// diffs where the lines are textual siblings.
#[must_use]
pub fn scan_diff(diff_text: &str, commit_msg: &str) -> Vec<Finding> {
    let intent = classify_intent(commit_msg);
    let mut findings: Vec<Finding> = Vec::new();

    // Per-file ordered lists, indexed by parse order. When a file
    // appears again later in the diff (multiple hunks), we keep
    // accumulating into the same lists so the i-th removed and i-th added
    // pair across the whole file, not per hunk.
    let mut files: Vec<(String, Vec<VersionLine>, Vec<VersionLine>)> = Vec::new();
    let mut current_path: Option<String> = None;
    // Post-image line counter, advanced on `+` and context lines.
    let mut post_line: u32 = 0;

    for line in diff_text.lines() {
        if let Some(rest) = line.strip_prefix("diff --git ") {
            // Begin a new file. find_or_create the file slot.
            let path = parse_diff_path(rest);
            current_path = Some(path.clone());
            files_entry(&mut files, &path);
            post_line = 0;
            continue;
        }
        // Hunk header: `@@ -a,b +c,d @@` (or `@@ -a +c @@` for one-line
        // hunks). Reset `post_line` to `c`.
        if line.starts_with("@@") {
            post_line = parse_hunk_post_start(line).unwrap_or(post_line);
            continue;
        }
        // Look up the path before parsing the +/- line. If no `diff --git`
        // header has been seen yet, the diff is malformed and we skip.
        let Some(path) = current_path.as_deref() else {
            continue;
        };
        if let Some(v) = parse_diff_line(line, path, post_line) {
            // Read the side before handing ownership to `push_to_file`; only
            // added lines advance the post-image counter.
            let advances_post_line = v.side == DiffSide::Added;
            push_to_file(&mut files, path, v);
            if advances_post_line {
                post_line = post_line.saturating_add(1);
            }
        } else if !line.starts_with('-') {
            // Context line — increments the post counter. Lines that are
            // neither `+`/`-` (hunk header already handled) or `\ No newline
            // at end of file` are harmless no-ops here.
            if !line.starts_with('\\') {
                post_line = post_line.saturating_add(1);
            }
        }
    }
    // Pair per-file, by ordered position within the file.
    for (_path, removed, added) in files {
        pair_file(&removed, &added, intent, &mut findings);
    }
    findings
}

/// Look up (or create) the per-file slot in `files`.
fn files_entry<'a>(
    files: &'a mut Vec<(String, Vec<VersionLine>, Vec<VersionLine>)>,
    path: &str,
) -> &'a mut (String, Vec<VersionLine>, Vec<VersionLine>) {
    // Resolve the position with an immutable scan first. Returning a `&mut`
    // borrow out of a conditional keeps that borrow alive across the later
    // `push` under NLL, so the index is taken before any mutation begins.
    let index = files
        .iter()
        .position(|(p, _, _)| p == path)
        .unwrap_or_else(|| {
            files.push((path.to_string(), Vec::new(), Vec::new()));
            files.len() - 1
        });
    &mut files[index]
}

/// Append a parsed `VersionLine` to the per-file slot matching its path.
fn push_to_file(
    files: &mut Vec<(String, Vec<VersionLine>, Vec<VersionLine>)>,
    path: &str,
    v: VersionLine,
) {
    let slot = files_entry(files, path);
    match v.side {
        DiffSide::Added => slot.2.push(v),
        DiffSide::Removed => slot.1.push(v),
    }
}

/// Pair a file's removed and added version lines by ordered position.
///
/// The standard unified-diff block shape (`-`s first, then `+`s) pairs
/// the `i`-th removed with the `i`-th added. A removal with no matching
/// addition is a pure deletion (the field disappeared) and is not a
/// movement finding; an addition with no matching removal is an insertion
/// paired against the sentinel `0.0.0` old value, which classifies
/// against any real `new` as Forward unless `new` is itself `0.0.0`.
fn pair_file(
    removed: &[VersionLine],
    added: &[VersionLine],
    intent: IntentDeclaration,
    findings: &mut Vec<Finding>,
) {
    let n = removed.len().max(added.len());
    for i in 0..n {
        let r = removed.get(i);
        let a = added.get(i);
        match (r, a) {
            (None, None) => (),
            (Some(r), None) => {
                // Lone removal — pure deletion; not a version movement. We
                // record nothing so the guard does not flag a removed
                // field (e.g. a `[bench]` stanza being deleted alongside
                // its siblings). The motivating incident adds a paired
                // `+` line for each removal, so this case is rare.
                let _ = r;
            }
            (Some(r), Some(a)) => push_pair(r, a, intent, findings),
            (None, Some(a)) => {
                // Lone addition — treat as `0.0.0 -> new` insertion.
                let synthetic = VersionLine {
                    path: a.path.clone(),
                    line_no: a.line_no,
                    version: String::from("0.0.0"),
                    side: DiffSide::Removed,
                    kind: a.kind,
                };
                push_pair(&synthetic, a, intent, findings);
            }
        }
    }
}

/// Push a single Finding from a removed/added pair.
fn push_pair(
    r: &VersionLine,
    a: &VersionLine,
    intent: IntentDeclaration,
    findings: &mut Vec<Finding>,
) {
    let direction = classify_pair(&r.version, &a.version);
    let message = format!(
        "{}:{} version {:?} -> {:?} ({})",
        a.path,
        a.line_no,
        r.version,
        a.version,
        direction_label(direction, intent),
    );
    findings.push(Finding {
        path: a.path.clone(),
        line_no: a.line_no,
        kind: a.kind,
        direction,
        intent,
        message,
    });
}

/// Render the short label used in the human-format finding message.
fn direction_label(direction: Direction, intent: IntentDeclaration) -> &'static str {
    match (direction, intent) {
        (Direction::Identical, _) => "identical",
        (Direction::Forward, IntentDeclaration::Declared) => "forward (intent declared)",
        (Direction::Forward, IntentDeclaration::Undeclared) => "forward (UNDECLARED)",
        (Direction::Backward, IntentDeclaration::Declared) => "BACKWARD (declared intent ignored)",
        (Direction::Backward, IntentDeclaration::Undeclared) => "BACKWARD",
    }
}

/// Parse the post-image path out of a `diff --git a/<x> b/<x>` header line.
/// The header line is the remainder after `diff --git `. Returns `b/<x>`
/// with the leading `b/` stripped; on a rename, the `b/` side is the
/// post-image path.
fn parse_diff_path(rest: &str) -> String {
    // `a/<path> b/<path>` optionally with surrounding quotes on Windows
    // symlinks. Take everything after the last ` b/` (or ` b"` for quoted).
    let rest = rest.trim();
    if let Some(idx) = rest.rfind(" b/") {
        rest[idx + 3..].to_string()
    } else if let Some(idx) = rest.rfind(" b\"") {
        rest[idx + 3..].trim_end_matches('"').to_string()
    } else {
        // Fall back to the entire remainder, which is unlikely to be useful
        // but at least keeps the audit running instead of panicking.
        rest.to_string()
    }
}

/// Parse the post-image start line number from a `@@ -a,b +c,d @@` hunk
/// header. Returns `None` for a malformed header.
fn parse_hunk_post_start(line: &str) -> Option<u32> {
    let plus = line.find('+')?;
    let rest = &line[plus + 1..];
    let end = rest.find(',')?;
    let c_str = rest.get(..end)?;
    c_str.parse::<u32>().ok()
}

/// True when any finding in the list is a defect: a backward movement, or a
/// forward movement with undeclared intent.
#[must_use]
pub fn has_defect(findings: &[Finding]) -> bool {
    findings.iter().any(|f| match f.direction {
        Direction::Backward => true,
        Direction::Forward => f.intent == IntentDeclaration::Undeclared,
        Direction::Identical => false,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_diff(body: &str) -> String {
        format!("diff --git a/Cargo.toml b/Cargo.toml\n{body}\n")
    }

    #[test]
    fn forward_with_declared_intent_is_clean() {
        let diff = make_diff("@@ -3,1 +4,1 @@\n-version = \"0.5.0\"\n+version = \"0.6.0\"\n");
        let findings = scan_diff(&diff, "chore(release): Bump workspace");
        assert!(findings.iter().all(|f| f.direction != Direction::Backward));
        assert!(
            findings
                .iter()
                .all(|f| f.direction == Direction::Forward
                    && f.intent == IntentDeclaration::Declared)
        );
        assert!(!has_defect(&findings));
    }

    #[test]
    fn backward_movement_is_always_defect_regardless_of_intent() {
        let diff = make_diff("@@ -3,1 +4,1 @@\n-version = \"0.5.0\"\n+version = \"0.4.1\"\n");
        let findings = scan_diff(&diff, "chore(release): Bump workspace");
        assert_eq!(findings.len(), 1);
        assert_eq!(findings[0].direction, Direction::Backward);
        assert!(has_defect(&findings));
    }

    #[test]
    fn forward_undeclared_is_defect() {
        let diff = make_diff("@@ -3,1 +4,1 @@\n-version = \"0.5.0\"\n+version = \"0.5.1\"\n");
        let findings = scan_diff(&diff, "fix(cfd-math): Tighten tolerance");
        assert_eq!(findings.len(), 1);
        assert_eq!(findings[0].direction, Direction::Forward);
        assert_eq!(findings[0].intent, IntentDeclaration::Undeclared);
        assert!(has_defect(&findings));
    }

    #[test]
    fn identical_reformat_is_not_defect() {
        let diff = make_diff("@@ -3,1 +4,1 @@\n-version = \"0.5.0\"\n+version = \"0.5.0\"\n");
        let findings = scan_diff(&diff, "style: Reformat Cargo.toml");
        assert_eq!(findings.len(), 1);
        assert_eq!(findings[0].direction, Direction::Identical);
        assert!(!has_defect(&findings));
    }

    #[test]
    fn three_surface_hermes_87ab265_pattern_is_flagged() {
        // The motivating incident touched the workspace version AND two
        // first-party inline-table dep entries (the per-crate
        // `hermes-simd-intrinsics = { path = "...", version = "0.4.0" }`
        // form, plus the workspace version). All three backward
        // movements must surface, even though the commit message declared
        // none as a release.
        let diff = "\
diff --git a/Cargo.toml b/Cargo.toml
@@ -14,1 +14,1 @@
-version = \"0.5.0\"
+version = \"0.4.1\"
diff --git a/crates/hermes-simd-core/Cargo.toml b/crates/hermes-simd-core/Cargo.toml
@@ -22,1 +22,1 @@
-hermes-simd-intrinsics = { path = \"../hermes-simd-intrinsics\", version = \"0.5.0\" }
+hermes-simd-intrinsics = { path = \"../hermes-simd-intrinsics\", version = \"0.4.0\" }
diff --git a/crates/hermes-simd-types/Cargo.toml b/crates/hermes-simd-types/Cargo.toml
@@ -11,2 +11,2 @@
-hermes-simd-core = { path = \"../hermes-simd-core\", version = \"0.5.0\", default-features = false }
+hermes-simd-core = { path = \"../hermes-simd-core\", version = \"0.4.0\", default-features = false }
";
        let findings = scan_diff(diff, "refactor(hermes): Replace git with path sources");
        assert_eq!(findings.len(), 3);
        for f in &findings {
            assert_eq!(f.direction, Direction::Backward, "{f:?}");
        }
        assert!(has_defect(&findings));
    }

    #[test]
    fn non_version_diff_is_empty() {
        let diff = make_diff("@@ -3,1 +4,1 @@\n-name = \"foo\"\n+name = \"bar\"\n");
        let findings = scan_diff(&diff, "refactor: Rename package");
        assert!(findings.is_empty());
    }

    #[test]
    fn addition_with_no_removal_pairs_against_zero_base() {
        let diff = make_diff("@@ -3,1 +4,1 @@\n+version = \"0.1.0\"\n");
        let findings = scan_diff(&diff, "chore(release): Initial release");
        assert_eq!(findings.len(), 1);
        assert_eq!(findings[0].direction, Direction::Forward);
        assert!(findings[0].intent == IntentDeclaration::Declared);
        assert!(!has_defect(&findings));
    }
}

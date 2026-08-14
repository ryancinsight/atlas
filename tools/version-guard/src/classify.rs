//! Direction classification for a single version-bearing diff line.
//!
//! Classification is a pure function over two semver strings — it has no I/O,
//! no mutation, and no error reporting channel: failures to parse either side
//! are treated as a backward movement so the guard fails loudly rather than
//! silently accepting a malformed version.
//!
//! # Intent
//!
//! Forward bumps are permitted only when the commit message declares a
//! release/bump intent — see [`IntentDeclaration`] for the recognised surface.
//! Backward movement is always a defect (quarantine by `git_discipline`),
//! regardless of declared intent.

use crate::parse::parse_semver;

/// Direction of version movement between two semver strings.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Direction {
    /// `X.Y.Z` -> `X.Y.Z` (no movement; possibly re-formatted). Not a defect.
    Identical,
    /// `X.Y.Z` -> `X'.Y'.Z'` with `X'.Y'.Z' > X.Y.Z`. Defect unless intent
    /// is declared in the commit message.
    Forward,
    /// `X.Y.Z` -> `X'.Y'.Z'` with `X'.Y'.Z' < X.Y.Z` (or either side failed
    /// to parse). Always a defect.
    Backward,
}

/// Whether the commit message declares a release/bump intent.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IntentDeclaration {
    /// The message carries one of: `chore(release)`, `build(deps)`, a
    /// `Bump:` trailer, or a `BREAKING CHANGE:` footer.
    Declared,
    /// The message declares none of the above; a forward bump is a defect.
    Undeclared,
}

/// Classify a pair of version strings as [`Direction::Identical`],
/// [`Direction::Forward`], or [`Direction::Backward`].
///
/// Malformed inputs (failed `parse_semver`) classify as backward: the guard
/// must fail loudly on a version it cannot reason about, never silently accept
/// an ill-formed value.
#[must_use]
pub fn classify_pair(old: &str, new: &str) -> Direction {
    match (parse_semver(old), parse_semver(new)) {
        (Some(a), Some(b)) if a == b => Direction::Identical,
        (Some(a), Some(b)) if b > a => Direction::Forward,
        _ => Direction::Backward,
    }
}

/// Inspect a commit message body and report whether it declares release/bump
/// intent. Recognised surface:
///
/// - `chore(release)` or `chore(release):` in the subject.
/// - `build(deps)` or `build(deps):` in the subject.
/// - A `Bump:` or `Bump-Decls:` trailer.
/// - A `BREAKING CHANGE:` footer.
///
/// The check is a substring scan over the message body. It is intentionally
/// conservative — it may report intent when none was meant (false positive),
/// but it must never miss a genuinely declared intent (false negative). A
/// false positive only means a forward bump is permitted, which is the
/// weaker direction; a false negative causes a valid release to fail the
/// guard.
#[must_use]
pub fn classify_intent(commit_msg: &str) -> IntentDeclaration {
    // Per-line scan so the substrings can anchor on the start of a line,
    // which matches the conventional-commit subject / footer shape.
    for line in commit_msg.lines() {
        let trimmed = line.trim_start();
        if trimmed.starts_with("chore(release)")
            || trimmed.starts_with("build(deps)")
            || trimmed.starts_with("Bump:")
            || trimmed.starts_with("Bump-Decls:")
            || trimmed.starts_with("BREAKING CHANGE:")
        {
            return IntentDeclaration::Declared;
        }
    }
    IntentDeclaration::Undeclared
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identical_versions_classify_as_identical() {
        assert_eq!(classify_pair("0.5.0", "0.5.0"), Direction::Identical);
    }

    #[test]
    fn forward_minor_bump_classifies_as_forward() {
        assert_eq!(classify_pair("0.5.0", "0.6.0"), Direction::Forward);
    }

    #[test]
    fn forward_patch_bump_classifies_as_forward() {
        assert_eq!(classify_pair("0.5.0", "0.5.1"), Direction::Forward);
    }

    #[test]
    fn forward_major_bump_classifies_as_forward() {
        assert_eq!(classify_pair("0.5.0", "1.0.0"), Direction::Forward);
    }

    #[test]
    fn backward_minor_classifies_as_backward() {
        assert_eq!(classify_pair("0.5.0", "0.4.1"), Direction::Backward);
    }

    #[test]
    fn backward_pre_release_release_classifies_as_forward() {
        // 0.5.0-beta.1 < 0.5.0 per SemVer, so 0.5.0 -> 0.5.0-beta.1 is
        // actually backward, and 0.5.0-beta.1 -> 0.5.0 is forward.
        assert_eq!(classify_pair("0.5.0", "0.5.0-beta.1"), Direction::Backward);
    }

    #[test]
    fn malformed_old_classifies_as_backward() {
        // A non-semver old value must not silently pass.
        assert_eq!(classify_pair("not-a-version", "0.5.0"), Direction::Backward);
    }

    #[test]
    fn malformed_new_classifies_as_backward() {
        assert_eq!(classify_pair("0.5.0", "not-a-version"), Direction::Backward);
    }

    #[test]
    fn both_malformed_classify_as_backward() {
        assert_eq!(classify_pair("nope", "also-nope"), Direction::Backward);
    }

    #[test]
    fn release_subject_declares_intent() {
        let msg = "chore(release): Bump workspace version to 0.5.0";
        assert_eq!(classify_intent(msg), IntentDeclaration::Declared);
    }

    #[test]
    fn build_deps_subject_declares_intent() {
        let msg = "build(deps): Update eunomia crate version";
        assert_eq!(classify_intent(msg), IntentDeclaration::Declared);
    }

    #[test]
    fn bump_trailer_declares_intent() {
        let msg = "fix(cfd-math): Repair convergence check\n\nBump: eunomia to 0.5.1";
        assert_eq!(classify_intent(msg), IntentDeclaration::Declared);
    }

    #[test]
    fn breaking_change_footer_declares_intent() {
        let msg = "refactor(cfd-math)!: Switch to Aequitas quantities\n\nBREAKING CHANGE: cfd_math::Field is now DimensionedField<S, D>.";
        assert_eq!(classify_intent(msg), IntentDeclaration::Declared);
    }

    #[test]
    fn unrelated_message_does_not_declare_intent() {
        let msg = "fix(cfd-math): Tighten the convergence tolerance derivation\n\nThe bound was previously O(n·ε); use the pairwise O(log n · ε) bound.";
        assert_eq!(classify_intent(msg), IntentDeclaration::Undeclared);
    }

    #[test]
    fn substring_in_a_non_anchor_position_does_not_falsely_declare() {
        // The substring "Bump:" appearing mid-line in the body must not be
        // mistaken for a trailer; the per-line scan anchored on the start
        // of the trimmed line protects against this.
        let msg =
            "fix(cfd-math): Repair convergence\n\nLook at the Bump: discussion in the design doc.";
        assert_eq!(classify_intent(msg), IntentDeclaration::Undeclared);
    }
}

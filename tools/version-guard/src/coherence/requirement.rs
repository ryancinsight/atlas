//! Cargo requirement evaluation through the `semver` crate.

use std::fmt;

use semver::{Version, VersionReq};
use serde::{Deserialize, Serialize};
use serde_json::value::RawValue;

/// One requirement evaluation requested by a batch caller.
#[derive(Debug, Deserialize)]
pub struct RequirementInput {
    /// Caller-owned identity copied unchanged to the result.
    pub id: Box<RawValue>,
    /// Complete semantic version to evaluate.
    pub version: String,
    /// Cargo version requirement to evaluate.
    pub requirement: String,
}

/// Semantic result for one batch row.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RequirementOutcome {
    /// The version satisfies the requirement.
    Satisfied,
    /// The version does not satisfy the requirement.
    Unsatisfied,
    /// The version is not valid semantic-version syntax.
    InvalidVersion,
    /// The requirement is not valid Cargo requirement syntax.
    InvalidRequirement,
}

/// One ordered requirement evaluation result.
#[derive(Debug, Serialize)]
pub struct RequirementOutput {
    /// Caller-owned identity copied from the input row.
    pub id: Box<RawValue>,
    /// Typed semantic result.
    pub outcome: RequirementOutcome,
    /// Parser diagnostic for an invalid version or requirement.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

#[derive(Debug)]
pub(crate) enum RequirementError {
    Version(semver::Error),
    Requirement(semver::Error),
}

impl fmt::Display for RequirementError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Version(source) => write!(formatter, "invalid selected version: {source}"),
            Self::Requirement(source) => {
                write!(formatter, "invalid Cargo requirement: {source}")
            }
        }
    }
}

/// Evaluate rows in input order while preserving each caller identity.
#[must_use]
pub fn evaluate_requirements(rows: Vec<RequirementInput>) -> Vec<RequirementOutput> {
    rows.into_iter()
        .map(|row| {
            let result = matches_requirement(&row.requirement, &row.version);
            let (outcome, error) = match result {
                Ok(true) => (RequirementOutcome::Satisfied, None),
                Ok(false) => (RequirementOutcome::Unsatisfied, None),
                Err(RequirementError::Version(source)) => {
                    (RequirementOutcome::InvalidVersion, Some(source.to_string()))
                }
                Err(RequirementError::Requirement(source)) => (
                    RequirementOutcome::InvalidRequirement,
                    Some(source.to_string()),
                ),
            };
            RequirementOutput {
                id: row.id,
                outcome,
                error,
            }
        })
        .collect()
}

pub(crate) fn matches_requirement(
    requirement: &str,
    actual: &str,
) -> Result<bool, RequirementError> {
    let actual = Version::parse(actual).map_err(RequirementError::Version)?;
    let requirement = VersionReq::parse(requirement).map_err(RequirementError::Requirement)?;
    Ok(requirement.matches(&actual))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cargo_requirement_forms_match_exactly() {
        let cases = [
            (">=0.46.1, <0.48", "0.48.0", false),
            ("<0.49", "0.48.0", true),
            ("0.8.0", "0.8.1", true),
            ("0.8.0", "0.9.0", false),
            ("0.0.3", "0.0.4", false),
            ("1.2", "1.9.0", true),
            ("~1.2.3", "1.2.9", true),
            ("~1.2.3", "1.3.0", false),
            ("=1.2.3", "1.2.3", true),
            ("1.2.*", "1.2.9", true),
            (">=1.2.3-alpha, <1.2.3", "1.2.3-alpha.2", true),
        ];
        for (requirement, version, expected) in cases {
            assert!(
                matches!(
                    matches_requirement(requirement, version),
                    Ok(actual) if actual == expected
                ),
                "unexpected result for {requirement} at {version}"
            );
        }
    }

    #[test]
    fn malformed_inputs_are_typed_without_interpreting_json_identity() {
        let rows: Vec<RequirementInput> = serde_json::from_str(
            r#"[{"id":18446744073709551617,"version":"1.2","requirement":"*"},{"id":18446744073709551618,"version":"1.2.3","requirement":"^1 || ^2"},{"id":{"$serde_json::private::Number":"123"},"version":"1.2.3","requirement":"*"},{"id":{"deep":[{"value":1.2300e+400}]},"version":"1.2.3","requirement":"*"}]"#,
        )
        .expect("invariant: static requirement rows are valid JSON");
        let results = evaluate_requirements(rows);
        assert_eq!(results[0].outcome, RequirementOutcome::InvalidVersion);
        assert_eq!(results[1].outcome, RequirementOutcome::InvalidRequirement);
        assert_eq!(results[2].outcome, RequirementOutcome::Satisfied);
        assert_eq!(results[3].outcome, RequirementOutcome::Satisfied);
        let expected = [
            "18446744073709551617",
            "18446744073709551618",
            r#"{"$serde_json::private::Number":"123"}"#,
            r#"{"deep":[{"value":1.2300e+400}]}"#,
        ];
        let output = serde_json::to_string(&results)
            .expect("invariant: requirement outputs contain valid raw JSON");
        for (row, expected) in results.iter().zip(expected) {
            assert_eq!(row.id.get(), expected);
            assert!(output.contains(&format!(r#""id":{expected}"#)));
        }
    }
}

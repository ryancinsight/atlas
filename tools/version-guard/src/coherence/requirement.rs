//! Cargo requirement evaluation through the `semver` crate.

use std::fmt;

use semver::{Version, VersionReq};
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// One requirement evaluation requested by a batch caller.
#[derive(Debug, Deserialize)]
pub struct RequirementInput {
    /// Caller-owned identity copied unchanged to the result.
    pub id: Value,
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
    pub id: Value,
    /// Typed semantic result.
    pub outcome: RequirementOutcome,
    /// Parser diagnostic for an invalid version or requirement.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

/// A malformed version or Cargo requirement.
#[derive(Debug)]
pub enum RequirementError {
    /// The selected version is malformed.
    Version {
        /// Input that failed to parse.
        value: String,
        /// Parser diagnostic.
        source: semver::Error,
    },
    /// The Cargo requirement is malformed.
    Requirement {
        /// Input that failed to parse.
        value: String,
        /// Parser diagnostic.
        source: semver::Error,
    },
}

impl fmt::Display for RequirementError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Version { value, source } => {
                write!(formatter, "invalid semantic version `{value}`: {source}")
            }
            Self::Requirement { value, source } => {
                write!(formatter, "invalid Cargo requirement `{value}`: {source}")
            }
        }
    }
}

impl std::error::Error for RequirementError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Version { source, .. } | Self::Requirement { source, .. } => Some(source),
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
                Err(RequirementError::Version { source, .. }) => {
                    (RequirementOutcome::InvalidVersion, Some(source.to_string()))
                }
                Err(RequirementError::Requirement { source, .. }) => (
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
    let actual = Version::parse(actual).map_err(|source| RequirementError::Version {
        value: actual.to_owned(),
        source,
    })?;
    let requirement =
        VersionReq::parse(requirement).map_err(|source| RequirementError::Requirement {
            value: requirement.to_owned(),
            source,
        })?;
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
    fn malformed_inputs_are_typed_results() {
        let results = evaluate_requirements(vec![
            RequirementInput {
                id: Value::from("version"),
                version: String::from("1.2"),
                requirement: String::from("*"),
            },
            RequirementInput {
                id: Value::from("requirement"),
                version: String::from("1.2.3"),
                requirement: String::from("^1 || ^2"),
            },
        ]);
        assert_eq!(results[0].outcome, RequirementOutcome::InvalidVersion);
        assert_eq!(results[1].outcome, RequirementOutcome::InvalidRequirement);
    }
}

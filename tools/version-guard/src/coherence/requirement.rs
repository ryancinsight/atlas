pub(crate) fn matches_requirement(requirement: &str, actual: &str) -> bool {
    // Prerelease and hyphen-range semantics are intentionally not approximated
    // by this small parser. Rejecting them is fail-closed; silently stripping
    // the prerelease would make an incoherent requirement appear clean.
    if requirement.contains('-') || actual.contains('-') {
        return false;
    }
    let Some(actual) = Version::parse(actual) else {
        return false;
    };
    requirement.split("||").any(|alternative| {
        alternative
            .split(',')
            .all(|token| matches_token(token.trim(), actual))
    })
}

fn matches_token(token: &str, actual: Version) -> bool {
    if token.is_empty() || token == "*" {
        return true;
    }
    let (operator, raw) = if let Some(rest) = token.strip_prefix(">=") {
        (">=", rest)
    } else if let Some(rest) = token.strip_prefix("<=") {
        ("<=", rest)
    } else if let Some(rest) = token.strip_prefix('>') {
        (">", rest)
    } else if let Some(rest) = token.strip_prefix('<') {
        ("<", rest)
    } else if let Some(rest) = token.strip_prefix('^') {
        ("^", rest)
    } else if let Some(rest) = token.strip_prefix('~') {
        ("~", rest)
    } else if let Some(rest) = token.strip_prefix('=') {
        ("=", rest)
    } else {
        ("^", token)
    };
    let raw = raw.trim();
    let parts: Vec<&str> = raw.split('.').collect();
    if parts
        .iter()
        .any(|part| *part == "*" || *part == "x" || *part == "X")
    {
        return parts
            .iter()
            .enumerate()
            .take_while(|(_, part)| !matches!(**part, "*" | "x" | "X"))
            .all(|(i, part)| actual.component(i) == part.parse::<u64>().ok());
    }
    let Some(version) = Version::parse_partial(raw) else {
        return false;
    };
    match operator {
        "^" => caret_matches(version, actual),
        "~" => actual >= version && actual < version.next_minor(),
        ">=" => actual >= version,
        "<=" => actual <= version,
        ">" => actual > version,
        "<" => actual < version,
        "=" => actual == version,
        _ => false,
    }
}

fn caret_matches(version: Version, actual: Version) -> bool {
    if actual < version {
        return false;
    }
    actual < version.caret_upper_bound()
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
struct Version {
    major: u64,
    minor: u64,
    patch: u64,
}

impl Version {
    fn parse(value: &str) -> Option<Self> {
        let mut parts = value
            .trim()
            .split('-')
            .next()?
            .split('+')
            .next()?
            .split('.');
        let version = Self {
            major: parts.next()?.parse().ok()?,
            minor: parts.next()?.parse().ok()?,
            patch: parts.next()?.parse().ok()?,
        };
        parts.next().is_none().then_some(version)
    }

    fn parse_partial(value: &str) -> Option<Self> {
        let mut parts = value
            .trim()
            .split('-')
            .next()?
            .split('+')
            .next()?
            .split('.');
        let version = Self {
            major: parts.next()?.parse().ok()?,
            minor: parts.next().map_or(Some(0), |v| v.parse().ok())?,
            patch: parts.next().map_or(Some(0), |v| v.parse().ok())?,
        };
        parts.next().is_none().then_some(version)
    }

    fn component(self, index: usize) -> Option<u64> {
        match index {
            0 => Some(self.major),
            1 => Some(self.minor),
            2 => Some(self.patch),
            _ => None,
        }
    }

    fn next_minor(self) -> Self {
        Self {
            major: self.major,
            minor: self.minor + 1,
            patch: 0,
        }
    }

    fn caret_upper_bound(self) -> Self {
        if self.major > 0 {
            Self {
                major: self.major + 1,
                minor: 0,
                patch: 0,
            }
        } else if self.minor > 0 {
            Self {
                major: 0,
                minor: self.minor + 1,
                patch: 0,
            }
        } else {
            Self {
                major: 0,
                minor: 0,
                patch: self.patch + 1,
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cargo_caret_requirements_accept_current_versions() {
        assert!(matches_requirement("0.8.0", "0.8.1"));
        assert!(!matches_requirement("0.8.0", "0.9.0"));
        assert!(matches_requirement("1.0", "1.4.0"));
    }

    #[test]
    fn wildcard_and_comparator_requirements_work() {
        assert!(matches_requirement("0.1.*", "0.1.9"));
        assert!(!matches_requirement("0.1.*", "0.2.0"));
        assert!(matches_requirement(">=0.8.0, <0.9.0", "0.8.4"));
    }

    #[test]
    fn strict_version_parser_rejects_extra_components() {
        assert!(Version::parse("1.2.3.4").is_none());
        assert!(Version::parse_partial("1.2.3.4").is_none());
    }
}

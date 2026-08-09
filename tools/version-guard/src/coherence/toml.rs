use std::collections::BTreeMap;

use super::manifest::DependencySpec;

pub(crate) fn sections(text: &str) -> BTreeMap<String, BTreeMap<String, String>> {
    let mut result: BTreeMap<String, BTreeMap<String, String>> = BTreeMap::new();
    let mut current = String::new();
    for line in logical_lines(text) {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if line.starts_with('[') && line.ends_with(']') {
            current = line[1..line.len() - 1].trim().to_string();
            result.entry(current.clone()).or_default();
            continue;
        }
        let Some((key, value)) = line.split_once('=') else {
            continue;
        };
        result.entry(current.clone()).or_default().insert(
            key.trim().trim_matches('"').to_string(),
            value.trim().to_string(),
        );
    }
    result
}

fn logical_lines(text: &str) -> Vec<String> {
    let mut result = Vec::new();
    let mut pending = String::new();
    let mut depth = 0_usize;
    for raw in text.lines() {
        let line = strip_comment(raw).trim();
        if line.is_empty() && pending.is_empty() {
            continue;
        }
        if !pending.is_empty() {
            pending.push(' ');
        }
        pending.push_str(line);
        depth += line.bytes().filter(|byte| *byte == b'{').count();
        depth = depth.saturating_sub(line.bytes().filter(|byte| *byte == b'}').count());
        if depth == 0 {
            result.push(std::mem::take(&mut pending));
        }
    }
    if !pending.is_empty() {
        result.push(pending);
    }
    result
}

fn strip_comment(line: &str) -> &str {
    let mut quoted = false;
    let mut escaped = false;
    for (index, byte) in line.bytes().enumerate() {
        match byte {
            b'"' | b'\'' if !escaped => quoted = !quoted,
            b'#' if !quoted => return &line[..index],
            b'\\' if quoted => escaped = !escaped,
            _ => escaped = false,
        }
    }
    line
}

pub(crate) fn section_value(
    sections: &BTreeMap<String, BTreeMap<String, String>>,
    section: &str,
    key: &str,
) -> Option<String> {
    let value = sections.get(section)?.get(key)?;
    Some(parse_string(value).unwrap_or_else(|| value.trim().to_string()))
}

pub(crate) fn section_flag(
    sections: &BTreeMap<String, BTreeMap<String, String>>,
    section: &str,
    key: &str,
) -> bool {
    sections
        .get(section)
        .and_then(|entries| entries.get(key))
        .is_some_and(|value| value.trim() == "true")
}

pub(crate) fn dependency_specs_from_sections(
    sections: &BTreeMap<String, BTreeMap<String, String>>,
    workspace_only: bool,
) -> Vec<DependencySpec> {
    let mut result = Vec::new();
    for (section, entries) in sections {
        let is_workspace = section == "workspace.dependencies";
        let is_dependency_table = section.ends_with(".dependencies")
            || matches!(
                section.as_str(),
                "dependencies" | "dev-dependencies" | "build-dependencies"
            );
        if !is_dependency_table || is_workspace != workspace_only {
            continue;
        }
        for (key, value) in entries {
            let table = parse_inline_table(value);
            let (key, dotted_workspace) = key
                .strip_suffix(".workspace")
                .map_or_else(|| (key.clone(), false), |base| (base.to_string(), true));
            let package = table.get("package").and_then(|v| parse_string(v));
            let version = table
                .get("version")
                .and_then(|v| parse_string(v))
                .or_else(|| parse_string(value));
            let workspace =
                dotted_workspace || table.get("workspace").is_some_and(|v| v.trim() == "true");
            let path = table.get("path").and_then(|v| parse_string(v));
            let git = table.get("git").and_then(|v| parse_string(v));
            let first_party_source = path.is_some() || git.is_some();
            result.push(DependencySpec {
                key,
                package,
                version,
                path,
                git,
                workspace,
                first_party_source,
            });
        }
    }
    result
}

fn parse_inline_table(value: &str) -> BTreeMap<String, String> {
    let value = value.trim();
    let inner = value
        .strip_prefix('{')
        .and_then(|v| v.strip_suffix('}'))
        .unwrap_or("");
    let mut result = BTreeMap::new();
    for part in split_commas(inner) {
        let Some((key, val)) = part.split_once('=') else {
            continue;
        };
        result.insert(key.trim().to_string(), val.trim().to_string());
    }
    result
}

fn split_commas(value: &str) -> Vec<&str> {
    let mut result = Vec::new();
    let mut start = 0;
    let mut quoted = false;
    for (index, byte) in value.bytes().enumerate() {
        if byte == b'"' {
            quoted = !quoted;
        } else if byte == b',' && !quoted {
            result.push(value[start..index].trim());
            start = index + 1;
        }
    }
    if start < value.len() {
        result.push(value[start..].trim());
    }
    result
}

fn parse_string(value: &str) -> Option<String> {
    let value = value.trim();
    let quote = value.chars().next()?;
    if quote != '"' && quote != '\'' {
        return None;
    }
    let value = &value[quote.len_utf8()..];
    let end = value.find(quote)?;
    Some(value[..end].to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn package_alias_is_parsed_from_inline_table() {
        let sections = sections(
            "[workspace.dependencies]\nmnemosyne = { package = \"mnemosyne-memory\", version = \"0.6.0\", git = \"https://example.invalid/mnemosyne\" }\n",
        );
        let deps = dependency_specs_from_sections(&sections, true);
        assert_eq!(deps[0].package.as_deref(), Some("mnemosyne-memory"));
        assert_eq!(deps[0].version.as_deref(), Some("0.6.0"));
        assert!(deps[0].first_party_source);
    }

    #[test]
    fn dotted_workspace_inheritance_and_multiline_table_are_parsed() {
        let sections = sections(
            "[package]\nversion.workspace = true\n[dependencies]\nprovider.workspace = true\nprovider = {\n  path = \"../provider\",\n  package = \"provider-core\",\n  version = \"0.1.0\"\n}\n",
        );
        assert!(section_flag(&sections, "package", "version.workspace"));
        let deps = dependency_specs_from_sections(&sections, false);
        assert_eq!(deps.len(), 2);
        assert_eq!(deps[0].key, "provider");
        assert!(deps.iter().any(|dep| {
            dep.package.as_deref() == Some("provider-core")
                && dep.version.as_deref() == Some("0.1.0")
                && dep.first_party_source
        }));
    }

    #[test]
    fn version_only_name_collision_is_not_first_party() {
        let sections = sections("[dependencies]\nprovider = \"0.1.0\"\n");
        let deps = dependency_specs_from_sections(&sections, false);
        assert!(!deps[0].first_party_source);
    }
}

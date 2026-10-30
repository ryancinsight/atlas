use std::path::{Path, PathBuf};

use super::View;
use super::member::Member;
use super::source::{ProviderId, path_provider};
use crate::Error;

fn member(path: &str, url: &str) -> Member {
    Member {
        path: PathBuf::from(path),
        url: url.to_string(),
    }
}

#[test]
fn ambiguous_path_identity_fails_instead_of_selecting_a_provider() {
    let mut members = vec![
        member("/stack/repos/provider", "https://example/left"),
        member("/stack/repos/provider", "https://example/right"),
    ];
    for _ in 0..2 {
        let error = path_provider(
            Path::new("/stack/repos/provider/crate"),
            &members,
            View::Remotes,
        )
        .expect_err("ambiguous provider identity");
        let Error::Manifest { path, message } = error else {
            panic!("expected ambiguous path error, got {error}");
        };
        assert_eq!(path, "/stack/repos/provider/crate");
        assert_eq!(message, "path names multiple registered providers");
        members.reverse();
    }
}

#[test]
fn most_specific_path_owner_is_independent_of_registration_order() {
    let mut members = vec![
        member("/stack/repos/provider", "https://example/left"),
        member("/stack/repos/provider", "https://example/right"),
        member("/stack/repos/provider/nested", "https://example/nested.git"),
    ];
    for _ in 0..2 {
        let resolved = path_provider(
            Path::new("/stack/repos/provider/nested/crate"),
            &members,
            View::Remotes,
        )
        .expect("most specific owner");
        assert_eq!(
            resolved,
            Some(ProviderId::Git("https://example/nested".to_string()))
        );
        members.reverse();
    }
}

#[test]
fn lexical_source_resolution_rejects_escape_and_textual_prefix_collisions() {
    let members = vec![member("/stack/repos/provider", "https://example/provider")];
    for path in [
        "/stack/repos/provider/../outside",
        "/stack/repos/provider-suffix",
    ] {
        let resolved =
            path_provider(Path::new(path), &members, View::Remotes).expect("resolve path");
        assert_eq!(resolved, None, "outside path {path}");
    }
}

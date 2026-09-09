#![expect(
    clippy::unwrap_used,
    reason = "test failures retain their diagnostic context"
)]

use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

use super::{BudgetError, Mode, Outcome, PreparedTarget, TargetSource, enforce};

struct Workspace {
    root: PathBuf,
}

impl Workspace {
    fn new() -> Self {
        // Only uniqueness is required; no other memory is published by the counter.
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let root = std::env::temp_dir().join(format!(
            "atlas-retained-benchmark-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir(&root).unwrap();
        std::fs::write(root.join("Cargo.toml"), "[package]\nname = \"retained-execution-test\"\nversion = \"0.0.0\"\nedition = \"2024\"\n[lib]\npath = \"lib.rs\"\n[workspace]\n").unwrap();
        std::fs::write(
            root.join("lib.rs"),
            "compile_error!(\"retained execution must not compile current source\");\n",
        )
        .unwrap();
        Self { root }
    }

    fn executable(&self, body: &str) -> PathBuf {
        #[cfg(windows)]
        let (name, header) = ("retained.cmd", "@echo off\r\n");
        #[cfg(not(windows))]
        let (name, header) = ("retained", "#!/bin/sh\n");
        let path = self.root.join(name);
        std::fs::write(&path, format!("{header}{body}")).unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o700)).unwrap();
        }
        path
    }
}

impl Drop for Workspace {
    fn drop(&mut self) {
        if let Err(error) = std::fs::remove_dir_all(&self.root) {
            eprintln!(
                "cannot remove test workspace {}: {error}",
                self.root.display()
            );
        }
    }
}

#[test]
fn zero_bound_is_rejected_before_preparing_either_source() {
    for source in [
        TargetSource::Compile { skip: Vec::new() },
        TargetSource::Retained(PreparedTarget {
            package: "apollo".to_owned(),
            name: "fft".to_owned(),
            executable: PathBuf::from("missing-benchmark"),
        }),
    ] {
        let error = enforce(
            std::path::Path::new("missing-manifest"),
            Mode::Timing,
            Duration::ZERO,
            source,
        )
        .unwrap_err();
        assert!(matches!(error, BudgetError::ZeroBound));
    }
}

#[test]
fn retained_execution_does_not_compile_current_source() {
    for code in [0, 17] {
        retained_exit_status(code);
    }
}

fn retained_exit_status(code: i32) {
    let workspace = Workspace::new();
    #[cfg(windows)]
    let body = format!("echo retained-executed>execution.marker\r\nexit /b {code}\r\n");
    #[cfg(not(windows))]
    let body = format!("printf 'retained-executed\\n' > execution.marker\nexit {code}\n");
    let executable = workspace.executable(&body);
    let selected = PreparedTarget {
        package: "retained-package".to_owned(),
        name: "retained-target".to_owned(),
        executable: executable.canonicalize().unwrap(),
    };
    let bound = Duration::from_secs(30);
    let enforcement = enforce(
        &workspace.root.join("Cargo.toml"),
        Mode::Examples,
        bound,
        TargetSource::Retained(selected.clone()),
    )
    .unwrap();
    assert_eq!(enforcement.mode, Mode::Examples);
    assert_eq!(enforcement.bound, bound);
    assert_eq!(enforcement.skipped, Vec::<String>::new());
    assert_eq!(enforcement.has_failures(), code != 0);
    let [result] = enforcement.results.as_slice() else {
        panic!("exactly the retained target must execute");
    };
    assert_eq!(result.target, selected);
    assert_eq!(
        std::fs::read_to_string(workspace.root.join("execution.marker"))
            .unwrap()
            .trim(),
        "retained-executed"
    );
    match &result.outcome {
        Outcome::Clean { .. } => assert_eq!(code, 0),
        Outcome::RunFailure { code: actual, .. } => assert_eq!(*actual, Some(code)),
        outcome @ Outcome::Breach { .. } => panic!("unexpected retained outcome: {outcome:?}"),
    }
}

#[test]
fn retained_execution_enforces_deadline() {
    let workspace = Workspace::new();
    // The fixture loops inside the supervised process; it creates no descendants.
    #[cfg(windows)]
    let body = ":running\r\ngoto running\r\n";
    #[cfg(not(windows))]
    let body = "while :; do :; done\n";
    let bound = Duration::from_millis(200);
    let enforcement = enforce(
        &workspace.root.join("Cargo.toml"),
        Mode::Examples,
        bound,
        TargetSource::Retained(PreparedTarget {
            package: "retained-package".to_owned(),
            name: "retained-target".to_owned(),
            executable: workspace.executable(body),
        }),
    )
    .unwrap();
    let [result] = enforcement.results.as_slice() else {
        panic!("exactly the retained target must execute");
    };
    assert_eq!(result.outcome, Outcome::Breach { bound });
    assert!(enforcement.has_failures());
}

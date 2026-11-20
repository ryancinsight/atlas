"""Source-to-binary identity coverage for the pinned SemVer checker."""
import os, shutil, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atlas_semver_tool as tool
class PreparedCheckerContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = tool.prepared_checker()
        cls.checker = cls.context.__enter__()
        cls.workspace = cls.checker.workspace
    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)
        if cls.workspace.exists():
            raise AssertionError(f"prepared checker workspace was not removed: {cls.workspace}")
    def test_exact_source_build_and_binary_are_recorded(self):
        evidence = self.checker.provenance
        self.assertEqual(evidence["version"], "cargo-semver-checks 0.51.0")
        self.assertEqual((evidence["source"]["revision"], evidence["source"]["tree"]),
            ("09a6b72abe23a0933e3acb998da7abb8b85ee826",
             "5f078e302a0df3db53dbf0f6b5c1d87f7cc46068"))
        self.assertEqual(evidence["build"]["config_overrides"], ["profile.release.lto=false"])
        build = next(record for record in evidence["build"]["commands"]
                     if "install" in record["command"])
        self.assertEqual(build["exit_code"], 0)
        self.assertIn("--locked", build["command"])
        self.assertNotIn("--force", build["command"])
        installed = shutil.which("cargo-semver-checks")
        if installed is not None:
            self.assertNotEqual(self.checker.executable, Path(installed).resolve())
    def test_missing_lock_and_wrong_manifest_are_rejected(self):
        source = self.workspace / "source"
        changed = self.workspace / "changed-source"
        changed.mkdir()
        shutil.copy2(source / "Cargo.toml", changed / "Cargo.toml")
        with self.assertRaisesRegex(RuntimeError, "manifest or lock differs"):
            tool._source_inputs(changed, evidence_pin(self.checker))
        shutil.copy2(source / "Cargo.lock", changed / "Cargo.lock")
        manifest = (changed / "Cargo.toml").read_text(encoding="utf-8")
        (changed / "Cargo.toml").write_text(
            manifest.replace('name = "cargo-semver-checks"', 'name = "other"', 1),
            encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(RuntimeError, "manifest or lock differs"):
            tool._source_inputs(changed, evidence_pin(self.checker))
    def test_compiler_overrides_and_process_failures_are_not_hidden(self):
        evidence = self.checker.provenance
        for name in ("CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER", "CARGO_BUILD_RUSTFLAGS",
                     "CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_RUSTFLAGS"):
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, name):
                tool._build_environment(
                    dict(os.environ, **{name: "--cfg checker_ambient"}),
                    evidence["build"]["tools"], evidence["source"],
                    Path(evidence["build"]["target_dir"]))
        records = []
        with self.assertRaisesRegex(RuntimeError, "exited 7"):
            tool._run([sys.executable, "-I", "-c", "raise SystemExit(7)"], self.workspace,
                      dict(os.environ), 30, records)
        self.assertEqual(records[0]["exit_code"], 7)
    def test_real_cargo_flags_and_ambient_config_are_refused(self):
        evidence, crate = self.checker.provenance, self.workspace / "ambient-crate"
        (crate / "src").mkdir(parents=True)
        (crate / "Cargo.toml").write_text(
            '[package]\nname="ambient"\nversion="0.1.0"\nedition="2024"\n', encoding="utf-8")
        (crate / "src/lib.rs").write_text(
            '#[cfg(not(checker_config))] compile_error!("config absent");\n', encoding="utf-8")
        home = crate / "cargo-home"
        home.mkdir()
        (home / "config.toml").write_text('[build]\nrustflags=["--cfg", "checker_config"]\n', encoding="utf-8")
        env = dict(os.environ, CARGO_HOME="cargo-home")
        check = [evidence["build"]["tools"]["cargo"]["path"], "check", "--manifest-path",
                 str(crate / "Cargo.toml")]
        tool._run(check, crate, env, 30, [])
        with self.assertRaisesRegex(RuntimeError, "ambient Cargo configuration"):
            tool._config_identity(crate, env, ())
    def test_binary_tamper_is_refused_before_use(self):
        changed = self.workspace / self.checker.executable.name
        shutil.copy2(self.checker.executable, changed)
        measured = tool._PreparedChecker(
            changed, self.checker.provenance, self.checker.sha256, self.workspace)
        changed.write_bytes(changed.read_bytes() + b"tampered")
        with self.assertRaisesRegex(RuntimeError, "changed during use"):
            measured.command(["--version"])
def evidence_pin(checker):
    return {name: checker.provenance["source"][name] for name in tool._PIN_FIELDS}

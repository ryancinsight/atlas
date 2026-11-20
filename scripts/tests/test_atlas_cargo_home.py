"""Cargo-home resolution and dep-info ownership regressions."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, SCRIPTS)
from atlas_cargo_home import cargo_home


def python_environment(**updates: str) -> dict[str, str]:
    environment = dict(os.environ, **updates)
    inherited = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join((SCRIPTS, inherited)) if inherited else SCRIPTS
    return environment


class CargoHomeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="atlas-cargo-home-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_explicit_homes_follow_cargo_resolution(self) -> None:
        command_root = self.root / "child"
        command_root.mkdir()
        profile = self.root / "profile"
        profile_variable = "USERPROFILE" if os.name == "nt" else "HOME"
        self.assertEqual(
            cargo_home({"CARGO_HOME": "", profile_variable: str(profile)}, command_root),
            profile / ".cargo",
        )
        self.assertEqual(
            cargo_home({"CARGO_HOME": "", profile_variable: "relative-profile"}, command_root),
            command_root / "relative-profile" / ".cargo",
        )
        self.assertEqual(
            cargo_home({"CARGO_HOME": "relative"}, command_root),
            command_root / "relative",
        )
        absolute = self.root / "absolute"
        self.assertEqual(cargo_home({"CARGO_HOME": str(absolute)}, command_root), absolute)
        with self.assertRaisesRegex(ValueError, "null character"):
            cargo_home({"CARGO_HOME": "invalid\0home"}, command_root)
        with self.assertRaisesRegex(ValueError, "command directory is relative"):
            cargo_home({"CARGO_HOME": "relative"}, Path("child"))
        if os.name == "nt":
            self.assertEqual(
                cargo_home({"cargo_home": "lower-case"}, command_root),
                command_root / "lower-case",
            )
            with self.assertRaisesRegex(ValueError, "multiple spellings"):
                cargo_home({"CARGO_HOME": "first", "cargo_home": "second"}, command_root)
            with self.assertRaisesRegex(ValueError, "drive-relative"):
                cargo_home({"CARGO_HOME": "C:relative"}, command_root)
        else:
            self.assertEqual(
                cargo_home({"CARGO_HOME": "", "HOME": str(profile), "cargo_home": "ignored"},
                           command_root),
                profile / ".cargo",
            )

    def test_os_fallback_ignores_environment_aliases(self) -> None:
        environment = python_environment()
        environment.pop("CARGO_HOME", None)
        if os.name == "nt":
            expected = Path(os.environ["USERPROFILE"]) / ".cargo"
            environment.pop("USERPROFILE", None)
            environment.update({"HOMEDRIVE": "Z:", "HOMEPATH": "\\different-profile"})
        else:
            import pwd

            expected = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".cargo"
            environment.pop("HOME", None)
        result = subprocess.run(
            [sys.executable, "-c", "from atlas_cargo_home import cargo_home; print(cargo_home())"],
            cwd=self.root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(Path(result.stdout.strip()), expected)

    def test_pinned_cargo_reads_empty_and_relative_configs(self) -> None:
        rustup = shutil.which("rustup")
        if rustup is None:
            raise AssertionError("rustup is required to resolve pinned Cargo 1.97")
        cargo = subprocess.run(
            [rustup, "which", "--toolchain", "1.97.0", "cargo"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        profile = self.root / "profile"
        cargo_config = profile / ".cargo"
        cargo_config.mkdir(parents=True)
        profile_config = cargo_config / "config.toml"
        profile_config.write_text("invalid = [\n", encoding="utf-8")
        crate = self.root / "crate"
        (crate / "src").mkdir(parents=True)
        (crate / "Cargo.toml").write_text(
            '[package]\nname="cargo-home-probe"\nversion="0.1.0"\nedition="2024"\n',
            encoding="utf-8",
        )
        (crate / "src/lib.rs").write_text("pub fn probe() {}\n", encoding="utf-8")
        environment = dict(os.environ, CARGO_HOME="")
        environment["USERPROFILE" if os.name == "nt" else "HOME"] = str(profile)
        result = subprocess.run(
            [cargo, "metadata", "--no-deps", "--format-version", "1", "--manifest-path",
             str(crate / "Cargo.toml")],
            cwd=crate,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 101, result.stderr)
        self.assertIn(str(profile_config), result.stderr)
        self.assertEqual(cargo_home(environment, crate), cargo_config)
        profile_variable = "USERPROFILE" if os.name == "nt" else "HOME"
        relative_profile = crate / "relative-profile"
        relative_profile_config = relative_profile / ".cargo" / "config.toml"
        relative_profile_config.parent.mkdir(parents=True)
        shutil.copy2(profile_config, relative_profile_config)
        relative_profile_environment = dict(os.environ, CARGO_HOME="")
        if os.name == "nt":
            for key in list(relative_profile_environment):
                if key.casefold() == profile_variable.casefold():
                    relative_profile_environment.pop(key)
            relative_profile_environment[profile_variable.lower()] = "relative-profile"
        else:
            relative_profile_environment[profile_variable] = "relative-profile"
        relative_profile_result = subprocess.run(
            [cargo, "metadata", "--no-deps", "--format-version", "1", "--manifest-path",
             str(crate / "Cargo.toml")],
            cwd=crate,
            env=relative_profile_environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(relative_profile_result.returncode, 101, relative_profile_result.stderr)
        self.assertIn(
            str(Path("relative-profile") / ".cargo" / "config.toml"),
            relative_profile_result.stderr,
        )
        self.assertEqual(
            cargo_home(relative_profile_environment, crate), relative_profile / ".cargo"
        )
        relative_home = crate / "relative-home"
        relative_home.mkdir()
        relative_config = relative_home / "config.toml"
        shutil.copy2(profile_config, relative_config)
        relative_environment = dict(os.environ, CARGO_HOME="relative-home")
        relative_result = subprocess.run(
            [cargo, "metadata", "--no-deps", "--format-version", "1", "--manifest-path",
             str(crate / "Cargo.toml")],
            cwd=crate,
            env=relative_environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(relative_result.returncode, 101, relative_result.stderr)
        self.assertIn(str(relative_config), relative_result.stderr)
        self.assertEqual(cargo_home(relative_environment, crate), relative_home)

    def test_dep_info_keeps_workspace_input_outside_actual_home(self) -> None:
        workspace = self.root / "workspace"
        package = workspace / "pkg"
        (package / "src").mkdir(parents=True)
        (workspace / "nested").mkdir()
        wrong_home = workspace / "relative-home"
        wrong_home.mkdir()
        tracked = wrong_home / "tracked.rs"
        tracked.write_text("pub const TRACKED: u8 = 1;\n", encoding="utf-8")
        (workspace / "Cargo.toml").write_text(
            '[workspace]\nmembers=["pkg"]\nresolver="3"\n', encoding="utf-8"
        )
        (package / "Cargo.toml").write_text(
            '[package]\nname="demo"\nversion="0.1.0"\nedition="2024"\n', encoding="utf-8"
        )
        (package / "src/lib.rs").write_text("pub fn demo() {}\n", encoding="utf-8")
        subprocess.run(
            ["git", "init", "-q"], cwd=workspace, check=True, capture_output=True, timeout=30
        )
        environment = python_environment(CARGO_HOME="relative-home")
        subprocess.run(
            [os.environ.get("CARGO", "cargo"), "generate-lockfile", "--offline"],
            cwd=workspace,
            env=environment,
            check=True,
            capture_output=True,
            timeout=60,
        )
        script = (
            "from pathlib import Path\n"
            "from atlas_build_dep_info import _stable_key, package_layout\n"
            f"workspace = Path({str(workspace)!r})\n"
            f"layout = package_layout(workspace / 'Cargo.toml', "
            f"Path({str(workspace / 'nested')!r}), Path({str(self.root / 'target')!r}))\n"
            "print(_stable_key(workspace / 'relative-home' / 'tracked.rs', 'demo', layout))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=workspace,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.stdout.strip(), "relative-home/tracked.rs")


if __name__ == "__main__":
    unittest.main()

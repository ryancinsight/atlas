"""Value-semantic configuration checks against the real Atlas source tree."""
import importlib.util
from pathlib import Path
import sys
import tomllib
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("atlas_metis", SCRIPTS / "atlas-metis.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class MetisConfigurationTests(unittest.TestCase):
    def test_preserves_profile_values_and_shared_cache(self):
        original = tomllib.loads((runner.ROOT / ".cargo/config.toml").read_text())
        actual = tomllib.loads(runner.cargo_configuration())
        self.assertEqual(actual["profile"], original["profile"])
        self.assertEqual(Path(actual["build"]["target-dir"]), runner.ROOT / "target")
        self.assertNotIn("patch", actual)
        expected = {key: value for key, value in original.items() if key != "patch"}
        expected["build"] = {**expected["build"], "target-dir": str(runner.ROOT / "target")}
        self.assertEqual(actual, expected)

    def test_configuration_keeps_canonical_dependency_sources(self):
        actual = tomllib.loads(runner.cargo_configuration())
        self.assertNotIn("patch", actual)
        lock = tomllib.loads(runner.WORKSPACE.with_name("Cargo.lock").read_text())
        moirai = next(package for package in lock["package"] if package["name"] == "moirai-webview")
        self.assertTrue(moirai["source"].startswith("git+https://github.com/ryancinsight/Moirai.git#"))
        self.assertEqual(tomllib.loads(runner.render(actual)), actual)

    def test_absolute_manifest_and_output_are_passed_to_metis(self):
        caller = runner.ROOT
        manifest = runner.STARTER
        self.assertEqual(runner.command_arguments(["apple", "run", "--target", "macos", "--output", "output/custom"], manifest, caller),
                         ["apple", "run", str(manifest), "--target", "macos", "--output", str(caller / "output/custom")])
        self.assertEqual(runner.command_arguments(["serve", "--port", "1420"], manifest, caller),
                         ["serve", str(manifest), "--port", "1420"])
        with self.assertRaisesRegex(ValueError, "apple requires build or run"):
            runner.command_arguments(["apple"], manifest, caller)


if __name__ == "__main__":
    unittest.main()

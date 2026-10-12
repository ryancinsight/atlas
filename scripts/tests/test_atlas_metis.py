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
        actual = tomllib.loads(runner.selected_configuration())
        self.assertEqual(actual["profile"], original["profile"])
        self.assertEqual(Path(actual["build"]["target-dir"]), runner.ROOT / "target")
        for source, packages in actual["patch"].items():
            for name, value in packages.items():
                expected = dict(original["patch"][source][name])
                expected["path"] = str(runner.ROOT / expected["path"])
                self.assertEqual(value, expected)
                self.assertTrue((Path(value["path"]) / "Cargo.toml").is_file())

    def test_provider_closure_excludes_unrelated_overlay_records(self):
        actual = tomllib.loads(runner.selected_configuration())
        names = {name for packages in actual["patch"].values() for name in packages}
        self.assertTrue({"moirai-webview", "moirai-pal", "moirai-transport", "moirai-core"} <= names)
        self.assertTrue({"ritk-dicom", "coeus-nn", "athena-core"}.isdisjoint(names))
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

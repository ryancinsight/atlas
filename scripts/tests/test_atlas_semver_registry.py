"""Check that release baselines come from prior stable, available versions."""

import unittest

from atlas_semver_registry import select_baseline


class BaselineSelectionTests(unittest.TestCase):
    def test_prior_compatible_index_entry_uses_numeric_version_order(self):
        rows = [{"vers": version, "yanked": yanked}
                for version, yanked in [("0.9.0", False), ("0.10.0", False),
                                        ("0.11.0", True), ("0.12.0-rc.1", False),
                                        ("0.12.0", False)]]
        self.assertEqual(select_baseline(rows, "0.12.0")["vers"], "0.10.0")

    def test_an_index_without_a_usable_prior_release_fails(self):
        with self.assertRaisesRegex(ValueError, "no usable earlier stable release"):
            select_baseline([{"vers": "0.1.0", "yanked": True}], "0.2.0")

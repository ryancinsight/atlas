"""Nontrivial coordinate/effect witnesses cannot qualify a framework runtime."""

import copy
from itertools import product
from pathlib import Path
import unittest
from unittest.mock import patch

from atlas_parity_core_math import (addresses, basic_view, broadcast, broadcast_view, evaluate_fixture,
                                    gather_pullback, negative_fixture_checks, verify_fixtures, view)
from atlas_parity_schema import ParityError, read_json

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "docs/parity/core-tensor/analytical-fixtures.json"


class CoreCoordinateTests(unittest.TestCase):
    def test_broadcast_zero_and_rank_zero(self):
        self.assertEqual(broadcast(), ())
        self.assertEqual(broadcast((), (2, 0, 3), (1, 3)), (2, 0, 3))
        self.assertEqual(broadcast((0,), (1,)), (0,))
        for other in [2, 3]:
            with self.assertRaises(ParityError):
                broadcast((0,), (other,))

    def test_dimension_partition_and_rank_extension_are_symmetric(self):
        values = [()] + [p for n in [1, 2] for p in product(range(4), repeat=n)]
        for left in values:
            for right in values:
                try:
                    forward = broadcast(left, right)
                except ParityError:
                    with self.assertRaises(ParityError):
                        broadcast(right, left)
                else:
                    self.assertEqual(forward, broadcast(right, left))
                    self.assertEqual(broadcast(forward, ()), forward)

    def test_offset_scalar_and_negative_strides(self):
        scalar = view((), (), 3, 8)
        self.assertEqual(addresses(scalar), [3])
        base = view((2, 3), (3, 1), 1, 8)
        reverse = basic_view(base, [{"kind": "integer", "index": -1},
                                    {"kind": "slice", "start": 2, "step": -1, "length": 3}])
        self.assertEqual(addresses(reverse), [6, 5, 4])

    def test_alias_footprint_and_broadcast_adjoint(self):
        base = view((1, 2), (2, 1), 2, 7)
        expanded = broadcast_view(base, (3, 2))
        self.assertEqual(addresses(expanded), [2, 3, 2, 3, 2, 3])
        self.assertEqual(gather_pullback(7, addresses(expanded), [2, -3, 5, 7, -11, 13]),
                         [0, 0, -4, 17, 0, 0, 0])
        self.assertEqual(set(addresses(expanded)), set(addresses(base)))

    def test_empty_shape_has_no_load_or_cotangent_contribution(self):
        empty = broadcast_view(view((1,), (1,), 2, 4), (0,))
        self.assertEqual(addresses(empty), [])
        self.assertEqual(gather_pullback(4, [], []), [0, 0, 0, 0])

    def test_empty_shape_never_materializes_other_axis_ranges(self):
        with patch("atlas_parity_core_math.product", side_effect=AssertionError("empty pool construction")):
            self.assertEqual(addresses(view((0, 10 ** 100), (1, 1), 0, 0)), [])

    def test_malformed_descriptors_and_trailing_adjoint_values_reject(self):
        for call in [lambda: broadcast((True,)), lambda: broadcast((-1,)),
                     lambda: view((2, 3), (1,), 0, 6), lambda: view((), (), 6, 6),
                     lambda: gather_pullback(2, [0], [2, 3]),
                     lambda: gather_pullback(10 ** 100, [], []),
                     lambda: basic_view(view((3,), (1,), 0, 3), [{"kind": "integer", "index": True}])]:
            with self.assertRaises(ParityError):
                call()

    def test_all_registered_exact_fixtures_and_wrong_values(self):
        fixtures = read_json(FIXTURE_PATH)["fixtures"]
        self.assertEqual(verify_fixtures(fixtures), 8)
        self.assertEqual(len(negative_fixture_checks(fixtures)), 8)

    def test_unknown_fields_and_unregistered_witness_do_not_gain_credit(self):
        fixtures = read_json(FIXTURE_PATH)["fixtures"]
        for change in [lambda r: r[0]["inputs"].update({"ignored": 1}),
                       lambda r: r[0].update({"ignored": 1}),
                       lambda r: r[0].update({"id": "CT-UNREGISTERED"}),
                       lambda r: r[1]["inputs"]["descriptor"].update({"ignored": 1}),
                       lambda r: r[2]["inputs"]["selectors"][0].update({"ignored": 1}),
                       lambda r: r[0].update({"expected": [2, False, 3]})]:
            altered = copy.deepcopy(fixtures)
            change(altered)
            with self.assertRaises(ParityError):
                verify_fixtures(altered)

    def test_binary64_collision_has_independent_spacing_explanation(self):
        # At exponent 53 binary64 spacing is two; ties round to the even significand.
        spacing = 2 ** (53 - 52)
        self.assertEqual(spacing, 2)
        self.assertEqual((2 ** 53) % spacing, 0)
        self.assertEqual((2 ** 53 + 1) % spacing, 1)
        row = next(r for r in read_json(FIXTURE_PATH)["fixtures"] if r["id"] == "CT-INT64-F64-LOSS")
        self.assertEqual(evaluate_fixture(row)["round_trip"], [2 ** 53, 2 ** 53])

    def test_correct_easy_cases_cannot_replace_named_boundaries(self):
        fixtures = read_json(FIXTURE_PATH)["fixtures"]
        changes = {
            "CT-ZERO-BROADCAST": {"shapes": [[], [2, 1, 3], [1, 3]]},
            "CT-RANK-ZERO": {"descriptor": view((1,), (1,), 3, 8)},
            "CT-REVERSE-OFFSET": {"descriptor": view((2, 3), (3, 1), 1, 8),
                                  "selectors": [{"kind": "integer", "index": 0},
                                                {"kind": "slice", "start": 0, "step": 1, "length": 3}]},
            "CT-EMPTY-VIEW": {"descriptor": view((3,), (1,), 2, 7),
                               "selectors": [{"kind": "slice", "start": 0, "step": 1, "length": 2}]},
            "CT-BROADCAST-ADJOINT": {"descriptor": view((1, 2), (2, 1), 2, 7),
                                      "target": [1, 2], "cotangents": [2, -3]},
            "CT-DUPLICATE-GATHER": {"storage_elements": 5, "locations": [0, 1, 2, 3],
                                    "cotangents": [3, -7, 11, 13]},
            "CT-NONAFFINE-RESHAPE": {"descriptor": view((2, 3), (3, 1), 0, 6)},
        }
        for identity, inputs in changes.items():
            altered = copy.deepcopy(fixtures)
            row = next(r for r in altered if r["id"] == identity)
            row["inputs"] = inputs
            row["expected"] = evaluate_fixture(row)
            with self.subTest(identity=identity), self.assertRaises(ParityError):
                verify_fixtures(altered)


if __name__ == "__main__":
    unittest.main()

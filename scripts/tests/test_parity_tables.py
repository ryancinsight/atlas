"""Storage transformations must conserve values and distinguish absent/null."""

import copy
import unittest

from atlas_parity_schema import ParityError
from atlas_parity_tables import pack, record_index, unpack


class TablesTests(unittest.TestCase):
    def setUp(self):
        self.records = [{"id": "a", "value": None}, {"id": "b"},
                        {"id": "c", "value": [True, 1, 1.0, {"x": "λ"}]},
                        {"id": "d", "value": [True, 1, 1.0, {"x": "λ"}]}]
        self.table = pack(self.records)

    def test_lossless_nested_values_and_absence(self):
        self.assertEqual(unpack(self.table), self.records)
        self.assertEqual(len(self.table["tables"]["value"]), 2)
        self.assertNotIn("value", unpack(self.table)[1])
        self.assertIsNone(unpack(self.table)[0]["value"])

    def test_invalid_cells_rejected(self):
        for cell in [True, -2, 100, "0", None]:
            with self.subTest(cell=cell):
                changed = copy.deepcopy(self.table)
                changed["rows"][0][0] = cell
                with self.assertRaises(ParityError):
                    unpack(changed)

    def test_duplicate_columns_rejected(self):
        self.table["columns"][1] = self.table["columns"][0]
        with self.assertRaises(ParityError):
            unpack(self.table)

    def test_missing_column_or_row_cell_rejected(self):
        for mutation in (lambda table: table["tables"].pop("value"),
                         lambda table: table["rows"][0].pop()):
            changed = copy.deepcopy(self.table)
            mutation(changed)
            with self.assertRaises(ParityError):
                unpack(changed)

    def test_duplicate_values_and_record_ids_rejected(self):
        self.table["tables"]["id"].append("a")
        with self.assertRaises(ParityError):
            unpack(self.table)
        with self.assertRaises(ParityError):
            record_index(pack([{"id": "a"}, {"id": "a"}]), "id")

    def test_nonfinite_json_rejected(self):
        with self.assertRaisesRegex(ParityError, "finite JSON"):
            pack([{"id": float("nan")}])


if __name__ == "__main__":
    unittest.main()

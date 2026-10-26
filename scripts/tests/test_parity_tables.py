"""Storage transformations must conserve values and distinguish absent/null."""

import copy
import enum
import sys
import unittest

from atlas_parity_schema import ParityError
from atlas_parity_tables import _value_key, canonical, pack, record_index, unpack


class DisplayInt(int):
    def __repr__(self):
        return "display is not JSON"

    def __int__(self):
        return 999


class DisplayString(str):
    def __str__(self):
        return "display is not JSON"


class DisplayList(list):
    def __repr__(self):
        return "display is not JSON"


class DisplayFloat(float):
    def __repr__(self):
        return "display is not JSON"


class Number(enum.IntEnum):
    ONE = 1


class String(enum.StrEnum):
    ONE = "one"


def slow_pack(records):
    """Original canonical-JSON deduplication oracle, without the scalar path."""
    columns = sorted(set().union(*(row.keys() for row in records)))
    tables = {column: [] for column in columns}
    indexes = {column: {} for column in columns}
    rows = []
    for record in records:
        row = []
        for column in columns:
            if column not in record:
                row.append(-1)
                continue
            key = canonical(record[column])
            if key not in indexes[column]:
                indexes[column][key] = len(tables[column])
                tables[column].append(record[column])
            row.append(indexes[column][key])
        rows.append(row)
    return {"format": "atlas-column-table-v1", "metadata": {},
            "columns": columns, "tables": tables, "rows": rows}


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

    def test_scalar_keys_match_original_json_equivalence(self):
        # Each pair is challenged against the original canonical serializer,
        # including values whose Python == relation is less discriminating.
        values = [None, False, True, 0, 1, -1, 10 ** 1000, 0.0, -0.0, 1.0,
                  1e300, "", "0", "true", "one", "\\n", "\n", "\"\\",
                  "λ", "\ud800", "\udc00", "\ud83d\ude00", "\U0001f600",
                  DisplayInt(1), Number.ONE, DisplayString("one"), String.ONE,
                  DisplayFloat(1.0), DisplayList([1, False]),
                  [], (), {}, [1, False], (1, False), {"x": [None, "λ"]},
                  {"x": (None, "λ")}, {"b": 1, "a": True}, {"a": True, "b": 1}]
        for left in values:
            for right in values:
                with self.subTest(left=ascii(left), right=ascii(right)):
                    self.assertEqual(canonical(left) == canonical(right),
                                     _value_key(left) == _value_key(right))
        records = [{"value": value} for value in values] + [{}, {"value": None}]
        self.assertEqual(canonical(pack(records)), canonical(slow_pack(records)))
        self.assertEqual(canonical(unpack(pack(records))), canonical(records))

    def test_mixed_builtin_and_fallback_duplicates_rejected(self):
        for left, right in [(DisplayInt(1), 1), (Number.ONE, 1),
                            (DisplayString("one"), "one"), (String.ONE, "one"),
                            ([1, False], (1, False))]:
            table = pack([{"value": left}])
            table["tables"]["value"].append(right)
            with self.assertRaisesRegex(ParityError, "duplicate table values"):
                unpack(table)

    def test_scalar_path_preserves_invalid_json_rejection(self):
        for value in [float("nan"), float("inf"), -float("inf"), object(),
                      {"nested": float("nan")}]:
            with self.assertRaisesRegex(ParityError, "finite JSON"):
                _value_key(value)
        limit = sys.get_int_max_str_digits()
        if limit:
            too_large = 10 ** limit
            with self.assertRaisesRegex(ParityError, "finite JSON"):
                canonical(too_large)
            with self.assertRaisesRegex(ParityError, "finite JSON"):
                _value_key(too_large)


if __name__ == "__main__":
    unittest.main()

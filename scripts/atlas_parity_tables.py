"""Lossless JSON record tables for large, reviewable source inventories.

Each column has an explicit value table. A cell is a nonnegative table index;
-1 alone means the key is absent. JSON null is a normal value, never absence.
This representation deduplicates storage, not APIs, signatures or semantics.
"""

import json

from atlas_parity_schema import ParityError, fields, need, unique


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ParityError("record table: value is not finite JSON") from error


def _value_key(value):
    """Exact canonical-JSON equality without encoding every scalar table cell.

    Tags keep bool, integer, float and string domains separate. Base-class
    accessors preserve JSON's handling of int/str subclasses without invoking
    their overridden display methods. Containers/floats retain the existing
    finite canonical serialization, including signed zero and key ordering.
    """
    if value is None:
        return (type(None),)
    if type(value) is bool:
        return (bool, value)
    if isinstance(value, str):
        return (str, str.__str__(value))
    if isinstance(value, int):
        try:
            return (int, int.__repr__(value))
        except ValueError as error:
            raise ParityError("record table: value is not finite JSON") from error
    return ('json', canonical(value))


def pack(records, metadata=None):
    need(type(records) is list and all(type(row) is dict for row in records),
         "record table: expected object records")
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
            key = _value_key(record[column])
            if key not in indexes[column]:
                indexes[column][key] = len(tables[column])
                tables[column].append(record[column])
            row.append(indexes[column][key])
        rows.append(row)
    return {"format": "atlas-column-table-v1", "metadata": metadata or {},
            "columns": columns, "tables": tables, "rows": rows}


def unpack(document):
    fields(document, {"format": str, "metadata": dict, "columns": list,
                      "tables": dict, "rows": list}, "record table")
    need(document["format"] == "atlas-column-table-v1", "unknown record-table format")
    columns, tables = document["columns"], document["tables"]
    need(all(type(key) is str for key in columns) and len(columns) == len(set(columns)) and
         set(columns) == set(tables), "record-table columns missing or duplicated")
    for column, values in tables.items():
        need(type(values) is list, f"{column}: value table must be a list")
        need(len(values) == len({_value_key(value) for value in values}),
             f"{column}: duplicate table values")
    records = []
    for row in document["rows"]:
        need(type(row) is list and len(row) == len(columns), "record-table row width differs")
        record = {}
        for column, cell in zip(columns, row):
            need(type(cell) is int and -1 <= cell < len(tables[column]),
                 f"{column}: invalid record-table cell")
            if cell >= 0:
                record[column] = tables[column][cell]
        records.append(record)
    return records


def record_index(document, key):
    return unique(unpack(document), key, "record table")

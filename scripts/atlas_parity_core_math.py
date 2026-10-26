"""Exact coordinate witnesses for a bounded tensor contract, not Atlas execution.

Dimensions are concrete nonnegative integers. Strides/offsets use element units
for a single positive-itemsize storage representation. Symbolic dimensions,
arbitrary byte strides, zero-itemsize descriptors and runtime adapters are not
silently classified by this mathematical model.
"""

import copy
import json
from itertools import product

from atlas_parity_schema import ParityError, need


def shape(value):
    need(type(value) in (list, tuple) and all(type(x) is int and x >= 0 for x in value),
         "coordinate model requires concrete nonnegative integer dimensions")
    return tuple(value)


def broadcast(*values):
    shapes = [shape(value) for value in values]
    rank = max(map(len, shapes), default=0)
    result = [1] * rank
    for current in shapes:
        for axis, extent in enumerate((1,) * (rank - len(current)) + current):
            prior = result[axis]
            need(prior == extent or prior == 1 or extent == 1, "incompatible concrete broadcast dimensions")
            if prior == 1:
                result[axis] = extent
    return tuple(result)


def coordinates(value):
    value = shape(value)
    # itertools.product constructs all input pools before producing one tuple.
    # An empty tensor has no coordinates even if another extent is enormous.
    if 0 in value:
        return iter(())
    return product(*(range(n) for n in value))


def view(value, strides, offset, storage_elements):
    value = shape(value)
    need(type(strides) in (tuple, list) and len(value) == len(strides) and
         all(type(x) is int for x in strides) and type(offset) is int and
         type(storage_elements) is int and storage_elements >= 0, "invalid affine storage descriptor")
    if all(value):
        low = offset + sum(min(0, (n - 1) * step) for n, step in zip(value, strides))
        high = offset + sum(max(0, (n - 1) * step) for n, step in zip(value, strides))
        need(0 <= low <= high < storage_elements, "nonempty view addresses escape storage")
    return {"shape": value, "strides": tuple(strides), "offset": offset, "storage_elements": storage_elements}


def addresses(descriptor):
    descriptor = checked_view(descriptor)
    count = 1
    for extent in descriptor["shape"]:
        count *= extent
    need(count <= 10000, "analytical witness materialization limit; not a reference API size limit")
    return [descriptor["offset"] + sum(index * step for index, step in zip(point, descriptor["strides"]))
            for point in coordinates(descriptor["shape"])]


def broadcast_view(descriptor, target):
    descriptor = checked_view(descriptor)
    target = shape(target)
    need(broadcast(descriptor["shape"], target) == target, "target cannot represent the source broadcast")
    padding = len(target) - len(descriptor["shape"])
    source = (1,) * padding + descriptor["shape"]
    strides = (0,) * padding + descriptor["strides"]
    result = [0 if n == 1 and out != 1 else step for n, out, step in zip(source, target, strides)]
    return view(target, result, descriptor["offset"], descriptor["storage_elements"])


def basic_view(descriptor, selectors):
    """Apply already-typed indices/slices/newaxes; Python binding rules are separate."""
    descriptor = checked_view(descriptor)
    need(type(selectors) is list, "typed selectors must be a finite list")
    output, strides, offset, axis = [], [], descriptor["offset"], 0
    for selector in selectors:
        need(type(selector) is dict and selector.get("kind") in {"integer", "slice", "newaxis"},
             "unknown typed basic selector")
        keys = {"newaxis": {"kind"}, "integer": {"kind", "index"},
                "slice": {"kind", "start", "step", "length"}}[selector["kind"]]
        need(set(selector) == keys, "unconsumed or missing selector fields")
        if selector["kind"] == "newaxis":
            output.append(1)
            strides.append(0)
            continue
        need(axis < len(descriptor["shape"]), "too many consuming selectors")
        extent, step = descriptor["shape"][axis], descriptor["strides"][axis]
        axis += 1
        if selector["kind"] == "integer":
            index = selector.get("index")
            need(type(index) is int, "integer selector is not a boolean or arbitrary coercion")
            index = index + extent if index < 0 else index
            need(0 <= index < extent, "integer selector outside axis")
            offset += index * step
        else:
            start, stride, length = (selector.get(key) for key in ("start", "step", "length"))
            need(all(type(x) is int for x in (start, stride, length)) and stride != 0 and length >= 0,
                 "invalid normalized slice")
            if length:
                need(0 <= start < extent and 0 <= start + (length - 1) * stride < extent,
                     "normalized nonempty slice escapes axis")
            offset += start * step
            output.append(length)
            strides.append(stride * step)
    output.extend(descriptor["shape"][axis:])
    strides.extend(descriptor["strides"][axis:])
    return view(output, strides, offset, descriptor["storage_elements"])


def checked_view(descriptor):
    need(type(descriptor) is dict and set(descriptor) == {"shape", "strides", "offset", "storage_elements"},
         "invalid coordinate descriptor fields")
    return view(descriptor["shape"], descriptor["strides"], descriptor["offset"], descriptor["storage_elements"])


def gather_pullback(storage_elements, locations, cotangents):
    """Transpose of a fixed gather matrix; repeated locations ADD contributions."""
    need(type(storage_elements) is int and storage_elements >= 0 and type(locations) is list and
         type(cotangents) is list and len(locations) == len(cotangents),
         "invalid gather adjoint dimensions")
    need(storage_elements <= 10000, "analytical adjoint materialization limit; not a reference API size limit")
    result = [0] * storage_elements
    for location, cotangent in zip(locations, cotangents):
        need(type(location) is int and 0 <= location < storage_elements, "invalid gather location")
        need(type(cotangent) is int, "this exact witness uses integer cotangents")
        result[location] += cotangent
    return result


# Every counted fixture is an exact bounded mathematical witness. The registry
# prevents adding unrelated or unevaluated rows to a reported verification count.
FIXTURES = {
    "CT-ZERO-BROADCAST": "broadcast", "CT-RANK-ZERO": "addresses",
    "CT-REVERSE-OFFSET": "basic_view", "CT-EMPTY-VIEW": "basic_view",
    "CT-BROADCAST-ADJOINT": "broadcast_pullback", "CT-DUPLICATE-GATHER": "gather_pullback",
    "CT-NONAFFINE-RESHAPE": "flat_affine", "CT-INT64-F64-LOSS": "binary64_integer_collision",
}


def evaluate_fixture(row):
    """Execute a closed coordinate model, never a comparator or provider adapter."""
    need(type(row) is dict and set(row) == {"id", "operation", "inputs", "expected", "model_credit"},
         "unconsumed or missing mathematical fixture fields")
    need(FIXTURES.get(row["id"]) == row["operation"], "fixture has no registered mathematical truth check")
    need(type(row["model_credit"]) is int and row["model_credit"] == 1, "invalid analytical witness credit")
    data, operation = row["inputs"], row["operation"]
    keys = {"broadcast": {"shapes"}, "addresses": {"descriptor"},
            "basic_view": {"descriptor", "selectors"},
            "broadcast_pullback": {"descriptor", "target", "cotangents"},
            "gather_pullback": {"storage_elements", "locations", "cotangents"},
            "flat_affine": {"descriptor"}, "binary64_integer_collision": {"integers"}}[operation]
    need(type(data) is dict and set(data) == keys, "unconsumed or missing fixture inputs")
    if operation == "broadcast":
        need(type(data["shapes"]) is list, "invalid broadcast shape sequence")
        return list(broadcast(*data["shapes"]))
    if operation == "addresses":
        return addresses(data["descriptor"])
    if operation == "basic_view":
        return addresses(basic_view(data["descriptor"], data["selectors"]))
    if operation == "broadcast_pullback":
        descriptor = broadcast_view(data["descriptor"], data["target"])
        return gather_pullback(descriptor["storage_elements"], addresses(descriptor), data["cotangents"])
    if operation == "gather_pullback":
        return gather_pullback(data["storage_elements"], data["locations"], data["cotangents"])
    if operation == "flat_affine":
        locations = addresses(data["descriptor"])
        # C-order enumeration admits one affine rank-one view exactly when its
        # consecutive differences agree. A false result requires another
        # representation/copy or the source API's specified rejection.
        steps = [b - a for a, b in zip(locations, locations[1:])]
        return {"addresses": locations, "rank_one_affine": len(set(steps)) <= 1}
    integers = data["integers"]
    need(type(integers) is list and len(integers) == 2 and all(type(x) is int for x in integers),
         "binary64 witness needs two exact integers")
    need(integers == [2 ** 53, 2 ** 53 + 1], "binary64 witness changed its declared representability boundary")
    # Integer round-trip uses Python's specified nearest binary64 conversion;
    # the independent test also proves this by spacing at exponent 53.
    return {"distinct_integers": integers[0] != integers[1],
            "binary64_equal": float(integers[0]) == float(integers[1]),
            "round_trip": [int(float(x)) for x in integers]}


def verify_fixtures(rows):
    need(type(rows) is list and len(rows) == len(FIXTURES) and
         {row.get("id") for row in rows if type(row) is dict} == set(FIXTURES),
         "mathematical fixture registry drift")
    for row in rows:
        actual = evaluate_fixture(row)
        witness_partition(row, actual)
        # Canonical JSON compares types too: False must never stand in for 0.
        need(json.dumps(actual, sort_keys=True) == json.dumps(row["expected"], sort_keys=True),
             f"{row['id']}: incorrect exact mathematical witness")
    return len(rows)


def witness_partition(row, actual):
    """A correct easy example cannot replace the named boundary being counted."""
    identity, data = row["id"], row["inputs"]
    if identity == "CT-ZERO-BROADCAST":
        values = data["shapes"]
        rank = max(map(len, values), default=0)
        padded = [(1,) * (rank - len(value)) + tuple(value) for value in values]
        need(any(not value for value in values) and len({len(value) for value in values}) > 1 and
             any(0 in axis and 1 in axis for axis in zip(*padded)) and 0 in actual,
             "zero broadcast witness lost its zero/unit/rank boundary")
    elif identity == "CT-RANK-ZERO":
        need(data["descriptor"]["shape"] == [] and data["descriptor"]["offset"] > 0,
             "rank-zero witness lost its scalar/nonzero-offset boundary")
    elif identity == "CT-REVERSE-OFFSET":
        need(data["descriptor"]["offset"] > 0 and len(actual) > 1 and
             all(a > b for a, b in zip(actual, actual[1:])) and
             any(s["kind"] == "integer" and s["index"] < 0 for s in data["selectors"]) and
             any(s["kind"] == "slice" and s["step"] < 0 for s in data["selectors"]),
             "reverse witness lost its negative-selection/offset boundary")
    elif identity == "CT-EMPTY-VIEW":
        need(actual == [] and any(s["kind"] == "slice" and s["length"] == 0 for s in data["selectors"]),
             "empty view witness lost its empty-slice boundary")
    elif identity in {"CT-BROADCAST-ADJOINT", "CT-DUPLICATE-GATHER"}:
        locations = (addresses(broadcast_view(data["descriptor"], data["target"]))
                     if identity == "CT-BROADCAST-ADJOINT" else data["locations"])
        seeds = data["cotangents"]
        need(len(set(locations)) < len(locations) and len(set(locations)) > 1 and
             any(x < 0 for x in seeds) and any(x > 1 for x in seeds),
             "adjoint witness lost repeated positions or signed nonunit cotangents")
        if identity == "CT-BROADCAST-ADJOINT":
            need(len(locations) > len(addresses(data["descriptor"])) and data["descriptor"]["offset"] > 0,
                 "broadcast adjoint witness lost expansion/nonzero offset")
    elif identity == "CT-NONAFFINE-RESHAPE":
        need(len(data["descriptor"]["shape"]) > 1 and actual["rank_one_affine"] is False and
             len(actual["addresses"]) > 2, "reshape witness lost its nonaffine enumeration boundary")


def negative_fixture_checks(rows):
    results = []
    for index, row in enumerate(rows):
        altered = copy.deepcopy(rows)
        altered[index]["expected"] = {"incorrect": row["id"]}
        try:
            verify_fixtures(altered)
        except ParityError:
            results.append(row["id"])
        else:
            need(False, "incorrect analytical witness accepted")
    return results

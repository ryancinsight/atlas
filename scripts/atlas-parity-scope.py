#!/usr/bin/env python3
"""Inspect retained public declarations and their framework-specific contracts."""

import argparse
import json

from atlas_parity import DEFAULT, load
from atlas_parity_schema import read_json
from atlas_parity_tables import unpack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol", help="Exact public spelling, or a full reference identity")
    parser.add_argument("--framework", choices=["numpy", "jax", "pytorch", "tensorflow"])
    args = parser.parse_args()
    bundle = load(DEFAULT)
    scope = bundle["public_scope"]
    tables, results = {}, []
    for identity, ref in bundle["references"].items():
        if args.symbol not in {identity, ref["symbol"]} or args.framework and args.framework != ref["framework"]:
            continue
        binding = scope["bindings"][identity]
        path = binding["source_artifact"]
        if path not in tables:
            tables[path] = unpack(read_json(DEFAULT / path))
        results.append({"reference": ref, "scope_binding": binding,
                        "contract": scope["contracts"][binding["contract"]],
                        "source_detail": tables[path][binding["source_row"]],
                        "semantic_mapping": next((row for row in bundle["mappings"].values()
                                                  if identity in row["reference_ids"]), None)})
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())

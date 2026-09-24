#!/usr/bin/env python3
"""Bind shared Cargo artifacts to their source tree and build dimensions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from atlas_build_identity import DEFAULT_LEASE_SECONDS, IdentityError, check_record, run_build


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    for mode in ("run", "check"):
        command = subparsers.add_parser(mode)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--package", required=True)
        command.add_argument("--target-dir", type=Path, required=True)
        command.add_argument("--profile", default="debug")
        command.add_argument("--target", default="host")
        command.add_argument("--features", default="")
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--artifact", type=Path, action="append", default=[])
        command.add_argument("command", nargs=argparse.REMAINDER)
        if mode == "run":
            command.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)
    args = parser.parse_args(argv)
    try:
        if args.mode == "check":
            code, value = check_record(
                args.root,
                args.package,
                args.target_dir,
                args.profile,
                args.target,
                args.features,
                args.artifact,
                args.manifest,
                args.command,
            )
            print(json.dumps(value, sort_keys=True))
            return code
        command = tuple(args.command)
        if command[:1] == ("--",):
            command = command[1:]
        result = run_build(
            args.root,
            args.manifest,
            args.package,
            args.target_dir,
            command,
            args.profile,
            args.target,
            args.features,
            args.artifact,
            lease_seconds=args.lease_seconds,
        )
        print(
            json.dumps(
                {
                    "status": result.status,
                    "record": result.record_path.as_posix(),
                    "cleaned": result.cleaned,
                    "artifacts": [path.as_posix() for path in result.artifact_files],
                },
                sort_keys=True,
            )
        )
        return 0
    except IdentityError as error:
        print(f"atlas-build-identity: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

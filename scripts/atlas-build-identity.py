#!/usr/bin/env python3
"""Bind shared Cargo artifacts to their source tree and build dimensions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from atlas_build_check import check_record
from atlas_build_identity import DEFAULT_LEASE_SECONDS, IdentityError, run_build
from atlas_cast_gate import (
    HISTORICAL_CAST_CONFIG,
    HISTORICAL_CAST_KEY,
    HISTORICAL_CAST_PROFILE,
    historical_cast_command,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    for mode in ("run", "check"):
        command = subparsers.add_parser(mode)
        command.add_argument("--root", type=Path, required=True)
        if mode == "run":
            command.add_argument(
                "--package",
                action="append",
                required=True,
                help="a package whose artifacts the run records; repeat for each, one record each",
            )
        else:
            command.add_argument("--package", required=True)
        command.add_argument(
            "--selection",
            action="append",
            default=[],
            help=(
                "a package the command builds, whether or not it is recorded; repeat for"
                " each (default: the --package set)"
            ),
        )
        command.add_argument("--target-dir", type=Path, required=True)
        command.add_argument("--profile", default="debug")
        command.add_argument("--target", default="host")
        command.add_argument("--features", default="")
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--command-cwd", type=Path, help="directory for the build command")
        command.add_argument("--command-key", help="stable key for the build dimensions")
        command.add_argument("--ignore-path", type=Path, action="append", default=[])
        command.add_argument("--artifact", type=Path, action="append", default=[])
        command.add_argument("command", nargs=argparse.REMAINDER)
        if mode == "run":
            command.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)
            command.add_argument(
                "--lease-wait-seconds",
                type=float,
                default=DEFAULT_LEASE_SECONDS,
                help="longest wait for a live owner, whatever its recorded expiry",
            )
    args = parser.parse_args(argv)
    try:
        command = tuple(args.command)
        if command[:1] == ("--",):
            command = command[1:]
        clean_config: tuple[str, ...] = ()
        if args.command_key == HISTORICAL_CAST_KEY:
            packages = [args.package] if args.mode == "check" else args.package
            if args.profile != "debug" or args.artifact or args.features:
                raise IdentityError("historical cast identity requires the ordinary debug selection")
            try:
                command = historical_cast_command(
                    command, root=args.root, manifest=args.manifest, command_cwd=args.command_cwd,
                    selection=args.selection or packages,
                )
            except (OSError, ValueError) as error:
                raise IdentityError(str(error)) from error
            args.profile = HISTORICAL_CAST_PROFILE
            clean_config = HISTORICAL_CAST_CONFIG[1:]
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
                command,
                args.command_cwd,
                args.command_key,
                args.ignore_path,
                args.selection,
            )
            print(json.dumps(value, sort_keys=True))
            return code
        results = run_build(
            args.root,
            args.manifest,
            tuple(args.package),
            args.target_dir,
            command,
            args.profile,
            args.target,
            args.features,
            args.artifact,
            lease_seconds=args.lease_seconds,
            lease_wait_seconds=args.lease_wait_seconds,
            command_cwd=args.command_cwd,
            command_key=args.command_key,
            ignore_paths=args.ignore_path,
            selection=args.selection,
            clean_config=clean_config,
        )
        # One JSON line per package, in `--package` order; `run_build` builds
        # a repeated package once and returns one result for it.
        for package, result in zip(dict.fromkeys(args.package), results, strict=True):
            print(
                json.dumps(
                    {
                        "package": package,
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

#!/usr/bin/env python3
"""Benchmark the Atlas provider-integration audit scenarios.

Each scenario executes the real audit subprocess. The benchmark records wall
time for repeated runs; it does not replace the audit's structural or
exact-head checks with a synthetic workload.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts" / "atlas-provider-integration-audit.py"
DEFAULT_ITERATIONS = 3
DEFAULT_TIMEOUT_SECONDS = 300.0


@dataclass(frozen=True)
class Scenario:
    """One auditable command in the benchmark matrix."""

    name: str
    command: tuple[str, ...]


def _audit_command(*options: str) -> tuple[str, ...]:
    return (
        sys.executable,
        str(AUDIT),
        "--provider-set",
        "requested-2026-08-14",
        "--format",
        "text",
        *options,
    )


def build_scenarios() -> tuple[Scenario, ...]:
    """Return the structural and exact-head audit scenarios."""

    return (
        Scenario(
            "requested-2026-08-14 structural-only",
            _audit_command("--structural-only"),
        ),
        Scenario(
            "requested-2026-08-14 exact-heads (default workers)",
            _audit_command("--exact-heads"),
        ),
        Scenario(
            "requested-2026-08-14 exact-heads (workers=1)",
            _audit_command("--exact-heads", "--exact-head-workers", "1"),
        ),
    )


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse benchmark controls with finite workload and timeout bounds."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations",
        type=_positive_int,
        default=DEFAULT_ITERATIONS,
        help="number of executions per scenario (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=_positive_float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="per-execution audit timeout (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable timing results",
    )
    return parser.parse_args(argv)


def _run_scenario(scenario: Scenario, iterations: int, timeout: float) -> dict[str, object]:
    durations: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        subprocess.run(
            scenario.command,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        durations.append(time.perf_counter() - started)

    return {
        "name": scenario.name,
        "iterations": iterations,
        "seconds": durations,
        "minimum_seconds": min(durations),
        "maximum_seconds": max(durations),
        "mean_seconds": sum(durations) / len(durations),
    }


def main(argv: list[str] | None = None) -> int:
    """Run every audit scenario and print measured wall-clock timings."""

    args = parse_args(argv)
    results = [
        _run_scenario(scenario, args.iterations, args.timeout_seconds)
        for scenario in build_scenarios()
    ]
    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    for result in results:
        print(
            f"{result['name']}: {result['iterations']} runs, "
            f"mean={result['mean_seconds']:.3f}s, "
            f"min={result['minimum_seconds']:.3f}s, "
            f"max={result['maximum_seconds']:.3f}s"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

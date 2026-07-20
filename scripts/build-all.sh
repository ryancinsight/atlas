#!/usr/bin/env bash
# Run a cargo command across every package workspace recorded in .gitmodules.
# Usage: ./scripts/build-all.sh [cargo-subcommand] [extra args...]
#   ./scripts/build-all.sh            # cargo build
#   ./scripts/build-all.sh nextest run # cargo nextest run
#   ./scripts/build-all.sh test --doc # cargo test --doc
#   ./scripts/build-all.sh clippy --all-targets -- -D warnings
set -euo pipefail

cmd="${1:-build}"
shift || true

if [ "$cmd" = "test" ]; then
    if ! printf '%s\n' "$@" | grep -qx -- '--doc'; then
        echo "Use 'nextest run' for tests; 'test --doc' is reserved for doctests." >&2
        exit 2
    fi
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

failed=()
found=0
while read -r module_key module_path; do
    if [ -z "$module_key" ] || [ -z "$module_path" ]; then
        echo "Invalid package-path record in $root/.gitmodules" >&2
        exit 1
    fi
    manifest="$root/$module_path/Cargo.toml"
    if [ ! -f "$manifest" ]; then
        echo "Recorded package is not initialized or has no manifest: $module_path" >&2
        exit 1
    fi
    found=1
    pkg="$(basename "$module_path")"
    echo "==> cargo $cmd ($pkg)"
    if ! cargo "$cmd" --manifest-path "$manifest" "$@"; then
        failed+=("$pkg")
    fi
done < <(git -C "$root" config -f .gitmodules --get-regexp '^submodule\..*\.path$')

[ "$found" -eq 1 ] || { echo "No package paths recorded in $root/.gitmodules" >&2; exit 1; }
if [ "${#failed[@]}" -ne 0 ]; then
    echo "Failed: ${failed[*]}" >&2
    exit 1
fi
echo "All packages succeeded: cargo $cmd"

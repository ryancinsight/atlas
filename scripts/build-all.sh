#!/usr/bin/env bash
# Run a cargo command across every package workspace under repos/.
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
repos="$root/repos"

failed=()
found=0
for dir in "$repos"/*/; do
    manifest="$dir/Cargo.toml"
    [ -f "$manifest" ] || continue
    found=1
    pkg="$(basename "$dir")"
    echo "==> cargo $cmd ($pkg)"
    if ! cargo "$cmd" --manifest-path "$manifest" "$@"; then
        failed+=("$pkg")
    fi
done

[ "$found" -eq 1 ] || { echo "No package workspaces found under $repos" >&2; exit 1; }
if [ "${#failed[@]}" -ne 0 ]; then
    echo "Failed: ${failed[*]}" >&2
    exit 1
fi
echo "All packages succeeded: cargo $cmd"

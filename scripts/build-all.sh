#!/usr/bin/env bash
# Run a cargo command across every package workspace under repos/.
# Usage: ./scripts/build-all.sh [cargo-subcommand] [extra args...]
#   ./scripts/build-all.sh            # cargo build
#   ./scripts/build-all.sh test       # cargo test
#   ./scripts/build-all.sh clippy --all-targets -- -D warnings
set -euo pipefail

cmd="${1:-build}"
shift || true

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

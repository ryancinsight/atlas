#!/usr/bin/env bash
# Prepare an Atlas shell for Cargo builds.
#
# Source this file so the environment changes remain in the current shell:
#   source scripts/atlas-toolchain-bootstrap.sh
#
# Or run one command with the prepared environment:
#   bash scripts/atlas-toolchain-bootstrap.sh cargo nextest run
#
# RUSTC/RUSTDOC must remain unset. Rustup's rustc proxy selects the committed
# rust-toolchain.toml for the current provider; a process-wide absolute path
# would silently bypass a provider pin. Empty overrides are especially harmful:
# Cargo then tries to execute ` -vV`.

atlas_bootstrap_toolchain() {
    unset RUSTC RUSTDOC

    local current_path="${PATH-}"
    local ucrt_bin="/ucrt64/bin"
    if [[ ! -d "$ucrt_bin" ]]; then
        return 0
    fi

    # Remove every existing occurrence, then put exactly one canonical entry
    # first. A mere "add if absent" leaves a foreign gcc earlier on PATH.
    local -a path_entries kept_entries
    local entry
    IFS=: read -r -a path_entries <<< "$current_path"
    for entry in "${path_entries[@]}"; do
        [[ "$entry" == "$ucrt_bin" ]] || kept_entries+=("$entry")
    done
    export PATH="$ucrt_bin"
    for entry in "${kept_entries[@]}"; do
        [[ -n "$entry" ]] && PATH+=":$entry"
    done
}

atlas_bootstrap_toolchain

# When executed rather than sourced, run the requested command in the prepared
# environment. With no command, print the effective environment for diagnostics.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ "$#" -gt 0 ]]; then
        exec "$@"
    fi
    printf 'RUSTC=%s\n' "${RUSTC-<unset>}"
    printf 'RUSTDOC=%s\n' "${RUSTDOC-<unset>}"
    printf 'PATH=%s\n' "$PATH"
fi

# Callers may source the file and invoke `atlas_bootstrap_toolchain` again after
# changing MSYS2 installation state.

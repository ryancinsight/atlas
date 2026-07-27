#!/usr/bin/env bash
# tools/_template/check-drift.sh
#
# Drift scanner for the Atlas coordinator-tool Cargo.toml /
# rust-toolchain.toml template. Verifies byte-level equality of the
# shared `[lints]`, `[profile.*]`, and (where present) shared
# [dependencies] keys between each consumer's `Cargo.toml` and
# `tools/_template/template-Cargo.toml`, plus the shared [toolchain]
# block in `rust-toolchain.toml`.
#
# Each extracted section starts at a top-level TOML heading (e.g.
# `[lints.rust]`) and ends at the next TOML heading or EOF, with any
# trailing comment-only lines trimmed — comment banners live in the
# template, not in consumers, so they are excluded from the
# canonical form the scanner compares.
#
# Exit codes:
#   0 — no drift detected across all consumers
#   1 — drift detected; the diff paths printed to stderr identify
#       the files the editor must reconcile
#
# Run locally before committing a Cargo.toml / rust-toolchain.toml
# policy change; wire into coordinator-tool CI per `engineering_gates`.
# Refs: backlog.md#ATLAS-TOOLS-TEMPLATE-EXTRACT-1.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
template_dir="$script_dir"
template_cargo="$template_dir/template-Cargo.toml"
template_toolchain="$template_dir/template-rust-toolchain.toml"

# Consumer list — keep in sync with tools/_template/README.md and the
# header comments of both template files. Adding a fourth coordinator
# tool means appending it here in the same change.
consumers=(
  "$script_dir/../checkout-path-dependencies"
  "$script_dir/../criterion-regression"
  "$script_dir/../gitlink-coherence"
)

# extract_section <file> <heading>
#
# Print the canonical TOML key=value block under <heading> in <file>:
# starts at the heading line, ends just before the next TOML heading
# (line beginning with `[`) or EOF, with any trailing comment-only
# lines (lines starting with `#` or blank) trimmed so inter-section
# banners in the template are excluded from comparison.
extract_section() {
  local file="$1"
  local heading="$2"
  awk -v h="$heading" '
    $0 == h { in_section = 1; next }
    in_section && /^\[/ { in_section = 0 }
    in_section { buf[NR] = $0 }
    END {
      # Trim trailing comment/blank lines.
      last = NR
      while (last > 0 && (buf[last] ~ /^#/ || buf[last] ~ /^[[:space:]]*$/)) last--
      for (i = 1; i <= last; i++) if (buf[i] != "") print buf[i]
    }
  ' "$file"
}

drift_detected=0

for consumer_dir in "${consumers[@]}"; do
  consumer_cargo="$consumer_dir/Cargo.toml"
  consumer_toolchain="$consumer_dir/rust-toolchain.toml"
  consumer_name="$(basename "$consumer_dir")"

  if [[ ! -f "$consumer_cargo" ]]; then
    echo "check-drift: $consumer_name missing Cargo.toml at $consumer_cargo" >&2
    drift_detected=1
    continue
  fi

  # 1. [lints.rust] — shared verbatim section.
  if ! diff -q \
      <(extract_section "$template_cargo" "[lints.rust]") \
      <(extract_section "$consumer_cargo" "[lints.rust]") >/dev/null 2>&1; then
    echo "check-drift: $consumer_name [lints.rust] drifts from template" >&2
    diff -u \
      <(extract_section "$template_cargo" "[lints.rust]") \
      <(extract_section "$consumer_cargo" "[lints.rust]") >&2 || true
    drift_detected=1
  fi

  # 2. [lints.clippy] — shared verbatim section.
  if ! diff -q \
      <(extract_section "$template_cargo" "[lints.clippy]") \
      <(extract_section "$consumer_cargo" "[lints.clippy]") >/dev/null 2>&1; then
    echo "check-drift: $consumer_name [lints.clippy] drifts from template" >&2
    diff -u \
      <(extract_section "$template_cargo" "[lints.clippy]") \
      <(extract_section "$consumer_cargo" "[lints.clippy]") >&2 || true
    drift_detected=1
  fi

  # 3. [profile.*] — four profile blocks shared verbatim across tools.
  for profile in \
      "[profile.dev]" \
      "[profile.dev.package.\"*\"]" \
      "[profile.test]" \
      "[profile.release]"; do
    if ! diff -q \
        <(extract_section "$template_cargo" "$profile") \
        <(extract_section "$consumer_cargo" "$profile") >/dev/null 2>&1; then
      echo "check-drift: $consumer_name $profile drifts from template" >&2
      diff -u \
        <(extract_section "$template_cargo" "$profile") \
        <(extract_section "$consumer_cargo" "$profile") >&2 || true
      drift_detected=1
    fi
  done

  # 4. [dependencies] — shared-case keys (serde, serde_json) are
  #    byte-compared only; a consumer may carry additional
  #    tool-specific deps that the template does not constrain.
  consumer_serde=$(awk '
    /^\[dependencies\]/ { in_deps = 1; next }
    /^\[/ && $0 != "[dependencies]" { in_deps = 0 }
    in_deps && /^serde[[:space:]]*=/ { print }
  ' "$consumer_cargo")
  template_serde=$(awk '
    /^\[dependencies\]/ { in_deps = 1; next }
    /^\[/ && $0 != "[dependencies]" { in_deps = 0 }
    in_deps && /^serde[[:space:]]*=/ { print }
  ' "$template_cargo")
  if [[ -n "$consumer_serde" ]] && \
     ! diff -q <(echo "$template_serde") <(echo "$consumer_serde") >/dev/null 2>&1; then
    echo "check-drift: $consumer_name [dependencies] serde family drifts from template" >&2
    diff -u <(echo "$template_serde") <(echo "$consumer_serde") >&2 || true
    drift_detected=1
  fi

  # 5. rust-toolchain.toml — byte-level equality of the [toolchain]
  #    block. Comments in the template describe the file's role but do
  #    not appear in consumers; the drift scanner extracts the
  #    [toolchain] block from each file and compares only those entries.
  if [[ ! -f "$consumer_toolchain" ]]; then
    echo "check-drift: $consumer_name missing rust-toolchain.toml at $consumer_toolchain" >&2
    drift_detected=1
  else
    template_tc=$(extract_section "$template_toolchain" "[toolchain]")
    consumer_tc=$(extract_section "$consumer_toolchain" "[toolchain]")
    if ! diff -q <(echo "$template_tc") <(echo "$consumer_tc") >/dev/null 2>&1; then
      echo "check-drift: $consumer_name rust-toolchain.toml [toolchain] drifts from template" >&2
      diff -u <(echo "$template_tc") <(echo "$consumer_tc") >&2 || true
      drift_detected=1
    fi
  fi
done

if (( drift_detected == 0 )); then
  echo "check-drift: ${#consumers[@]} consumers clean against tools/_template/"
  exit 0
fi

echo "check-drift: drift detected in one or more coordinator tools; reconcile with tools/_template/" >&2
exit 1

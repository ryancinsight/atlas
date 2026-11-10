# ADR 0071: The stack config owns build profiles; optimization raises are named there

Status: Accepted

## Context

Every member builds into one shared Cargo target (`.cargo/config.toml`,
`build.target-dir`). Cargo keys each artifact on its resolved profile, so
members whose manifests chose different development profiles each compiled
their own copy of every shared dependency. Measured 2026-09-22: one library
carried 19 fingerprint variants across 4 profile hashes within 14 hours, and
`debug/deps` held 10.3 GiB of rlibs beyond one copy per crate. The root
configuration therefore sets `opt-level = 0` for `[profile.dev]`,
`[profile.test]` and both `package."*"` tables; config profiles override
manifest profiles, so that value holds for every build rooted under the stack.

The push gate builds an export of the pushed revision under a mirror of that
configuration. Numeric simulation tests then run unoptimized. On 2026-11-10
three pushes of ryancinsight/kwavers#1024, the cure for a red default branch, expired
on the gate's 600-second deadline inside the test stage. CI was unaffected: it
builds outside the stack, where the kwavers manifest's `opt-level = 1` applies.

This record is as-built for the first paragraph and new for the decision
below. No earlier ADR covers build profiles.

## Decision

The stack configuration is the only owner of hash-bearing profile keys. A
crate is optimized above 0 for development and test builds only by a named
entry in that file's `[profile.dev.package]` table, at `opt-level = 1`, and
only on a measurement that names the gate run it unblocks. `[profile.test]`
inherits the named entries; a named entry keeps the wildcard's `debug = false`
for a dependency and the root profile's line tables for a workspace member.

The first set is the 23 kwavers crates and 30 first-party provider crates
they compute through (apollo, eunomia, hermes, leto, mnemosyne, moirai).

## Evidence

The head of ryancinsight/kwavers#1024 on 2026-11-10, `cargo nextest run
-p kwavers-analysis -p kwavers`, 1279 tests, one host, nextest per-test times
summed. "251 tests" are the tests the
gate finished before its deadline, matched by name across runs.

| Crates at opt-level 1 | 251 tests | All 1279 | Wall |
|---|---|---|---|
| None (stack config as it was) | 610 s | not reached | deadline, 600 s |
| kwavers crates (23) | 395 s | 763 s | 346 s |
| and apollo, eunomia, hermes, leto (10) | 218 s | 560 s | 221 s |
| and mnemosyne, moirai (20): the adopted set | 188 s | 503 s | 179 s |
| and athena, coeus (10): not adopted | 188 s | 516 s | 182 s |
| Everything (kwavers manifest, outside the stack) | 99 s | 412 s | 75 s |

Wall times were taken under different concurrent load; the sums rank the
sets. The adopted row ran in configuration form on a fresh export: clippy
`--all-targets` 110 s, test build 147 s, tests 179 s, 468 s to the end of the
test stage with every kwavers crate rebuilt at the new level. The gate then
documents the packages and verifies artifact identity, 35 s and 164 s on a
kwavers-transducer push the same day, so the first push after the profile
changes builds the cache and a following push uses it.

Witnessed in configuration form with `cargo build --message-format=json`:
`opt_level` 1 for `kwavers-core`, `eunomia`, `leto` and `moirai-core` under
both `dev` and `test`, 0 for unnamed dependencies, and no warning for a name
absent from the build graph.

## Rejected alternatives

- **Wildcard raise** (`package."*"` at 1 or higher). It keeps one copy per
  crate but optimizes every dependency of every member for a need two
  packages measured, and it removes the measurement that justifies each
  entry.
- **Named raises in the member manifest.** They apply under the stack
  configuration, since a named spec is more specific than the wildcard, but
  each raising member gets its own copy of the providers it names, which is
  the duplication the configuration removes. A root-manifest change also
  makes the gate select every package of that member.
- **A longer gate deadline, or skipping the gate.** The deadline is the
  budget; a run that misses it is the defect.
- **Smaller test workloads.** The tests are the specification of the
  solvers; shrinking them to fit an unoptimized build weakens it.

## Consequences

- Raising a provider changes its profile hash for every member, so each
  dependent rebuilds once after the configuration reaches a checkout.
- The gate mirrors the configuration file on disk above the member, so a
  landed change takes effect for pushes once the stack-root checkout carries
  it.
- A member whose gate misses the deadline for the same cause adds its crates
  here with its measurement; it does not add a manifest raise.
- Existing member-manifest profile keys stay for builds rooted outside the
  stack (CI). They are inert inside it.

## Overturning evidence

- Shared-cache growth attributable to the raised copies that exceeds the
  growth the wildcard-0 rule removed.
- A gate run that still misses its deadline with its hot crates named, which
  moves the remedy to the gate's per-push rebuild of workspace crates or to
  the suite's process count.
- Cargo sharing artifacts across profile hashes, which would remove the
  reason for one stack-wide value.

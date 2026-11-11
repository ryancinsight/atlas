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

The first set is the 23 kwavers crates and ten first-party provider crates
they compute through (apollo, eunomia, hermes, leto).

## Evidence

The head of ryancinsight/kwavers#1024 on 2026-11-10, `cargo nextest run
-p kwavers-analysis -p kwavers`, 1279 tests, on one host that other builds
share. Per-test times vary with that load: two gate runs of the unchanged
configuration differ by a factor of 1.51 in the summed time of the 152 tests
both logs hold (313.0 s and 472.9 s). A group is therefore named only on a
replicated comparison: baseline and candidate run interleaved twice on one
fresh export, compared by the median per-test time ratio over the tests at
1 s or more in the first baseline run. The band is the two
same-configuration medians and their reciprocals; a group is measured when
all four candidate-to-baseline medians lie below the band. Each rule was
posted on the pull request before its runs.

| Group | Baseline | Tests | Band | Four medians | Result |
|---|---|---|---|---|---|
| kwavers (23) | 30 providers | 61 | 0.907 to 1.103 | 0.648 to 0.759 | measured |
| apollo, eunomia, hermes, leto (10) | kwavers | 124 | 0.916 to 1.091 | 0.293 to 0.457 | measured |
| mnemosyne, moirai (20) | the 33 above | 51 | 0.850 to 1.176 | 0.800 to 1.070 | not shown |

- **kwavers crates.** Measured with all 30 providers raised, not with the
  ten that are named. Carrying the result to the named set assumes the gain
  does not depend on mnemosyne and moirai being raised; no run compares the
  ten providers alone with the named 33.
- **apollo, eunomia, hermes, leto.** 109 to 121 of the 124 tests are faster in
  each pairing. All four runs started with no compiler process running; the
  second candidate command recompiled 99 units before its tests.
- **mnemosyne, moirai: not named.** One median lies below the band (0.800);
  three lie inside it (0.887, 0.993, 1.070). The second candidate run did
  not get a quiet host: it waited the full 600 s, started with four compiler
  processes running, recompiled 176 units and waited on the build-directory
  lock once and on the package-cache lock five times. That shows neither a
  step nor its absence; under the rule the names stay out.

Single runs earlier the same day, unreplicated, for scale. "251 tests" are
the PASS lines that survive in the truncated log of the gate run that
expired (positions 94 to 344 of 1279), matched by name in the other runs.

| Crates at opt-level 1 | 251 tests | All 1279 | Nextest summary |
|---|---|---|---|
| None (stack config as it was) | 611 s | not reached | deadline, 600 s |
| kwavers crates (23) | 395 s | 763 s | 346 s |
| and apollo, eunomia, hermes, leto: the named set | 218 s | 560 s | 221 s |
| and mnemosyne, moirai: not named | 188 s | 503 s | 179 s |
| and athena, coeus: not named, not replicated | 188 s | 516 s | 182 s |
| Everything (kwavers manifest, outside the stack) | 99 s | 412 s | 75 s |

Stage commands of the named set in the second ablation, into the shared
target: clippy `--all-targets` 124 s (5 units compiled, 81 checked); test
build 169 s (83 units compiled); test command 279 s, of which the build phase
reports 63 s for one recompiled unit and nextest 174 s; test command again 372
s, of which the build phase reports 139 s for 99 recompiled units and nextest
203 s. The gate then documents the packages and verifies artifact identity, 35
s and 164 s on a kwavers-transducer push the same day. Run in sequence as
measured, clippy, test build, nextest and those two stages sum to 666 s, above
the 600 s deadline, so the first push after the configuration reaches a
checkout is expected to expire. With the test binaries built, a test command
and the two closing stages take 478 s (571 s with the second command), which
leaves 122 s (29 s) for clippy. Gate fit is therefore not established: it
depends on how many units a push rechecks and recompiles, and no gate run
under this configuration exists. The real push of kwavers#1024 is its test.

Not measured: any member other than kwavers, including what compiling the ten
providers at level 1 costs its builds, and the rebuild of the kwavers crates
at level 1 on a push beyond the unit counts above.

Witnessed with `cargo build --message-format=json` and `cargo test --no-run`
for `kwavers-core`: `opt_level` 1 for every named crate in the graph, 0 for
unnamed dependencies and build scripts, and no warning for a name absent from
the graph.

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
  dependent rebuilds once after the configuration reaches a checkout. That
  rebuild falls inside the member's next gate run; its cost is measured for
  kwavers only.
- The gate mirrors the configuration file on disk above the member, so a
  landed change takes effect for pushes once the stack-root checkout carries
  it.
- A member whose gate misses the deadline for the same cause adds its crates
  here with its measurement; it does not add a manifest raise.
- Member-manifest profile keys stay for builds rooted outside the stack
  (CI). Inside it the configuration overrides only the keys it sets: a
  manifest's root development and test `opt-level` and `debug` are inert,
  while keys the configuration leaves alone (release `lto`, `codegen-units`,
  `overflow-checks`, a custom profile) still apply.

## Overturning evidence

- Shared-cache growth attributable to the raised copies that exceeds the
  growth the wildcard-0 rule removed.
- A gate run that still misses its deadline with its hot crates named, which
  moves the remedy to the gate's per-push rebuild of workspace crates or to
  the suite's process count.
- Cargo sharing artifacts across profile hashes, which would remove the
  reason for one stack-wide value.

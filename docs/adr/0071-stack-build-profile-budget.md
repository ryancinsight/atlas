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
-p kwavers-analysis -p kwavers`, 1279 tests, on one host that other builds
shared. Nextest's per-test times vary with that load: two gate runs of the
unchanged configuration differ by a factor of 1.51 in the summed time of the
152 tests both logs hold (313.0 s and 472.9 s). A sum therefore separates two
sets only when the difference exceeds a same-configuration replicate.

Single runs, as taken. "251 tests" are the PASS lines that survive in the
truncated log of the gate run that expired (positions 94 to 344 of 1279),
matched by name in the other runs.

| Crates at opt-level 1 | 251 tests | All 1279 | Wall |
|---|---|---|---|
| None (stack config as it was) | 611 s | not reached | deadline, 600 s |
| kwavers crates (23) | 395 s | 763 s | 346 s |
| and apollo, eunomia, hermes, leto (10) | 218 s | 560 s | 221 s |
| and mnemosyne, moirai (20): the adopted set | 188 s | 503 s | 179 s |
| and athena, coeus (10): not adopted | 188 s | 516 s | 182 s |
| Everything (kwavers manifest, outside the stack) | 99 s | 412 s | 75 s |

What the runs establish, group by group:

- **The adopted set against none.** On the 152 tests both unraised gate
  runs hold, 134.7 s against 313.0 s for the faster of the two.
- **apollo, eunomia, hermes, leto.** On those 152 tests, 302.0 s with the
  kwavers crates alone and 152.4 s with these ten added.
- **mnemosyne, moirai.** Of the 56 tests at 1 s or more before the step, 50
  are faster after it, and 47 of those are also faster in the athena and
  coeus run, an independent run of a superset. Median per-test ratios 0.855
  and 0.844.
- **athena, coeus: not adopted.** Median per-test ratio 1.014 against the
  adopted set on those 56 tests.
- **The kwavers crates.** The single runs do not isolate them, so an
  ablation did: 30 providers (A) against the adopted 53 (B) on one fresh
  export, runs interleaved A, B, A, B, rule fixed before the runs. On the 61
  tests at 1 s or more in the first A run, the same-configuration medians are
  1.038 (A/A) and 0.907 (B/B), a band of 0.907 to 1.103; the four B/A medians
  are 0.759, 0.731, 0.658 and 0.648. 56 of the 61 are faster in B.

Stage times of the adopted set on a fresh export, one run: clippy
`--all-targets` 110 s, test build 147 s, tests 179 s, 468 s to the end of the
test stage with every kwavers crate rebuilt at the new level. The ablation
repeated the B stages while another build held the processors at full load
and the target lock: clippy 127 s, test build 195 s, test commands 295 s and
316 s. The gate then documents the packages and verifies artifact identity,
35 s and 164 s on a kwavers-transducer push the same day. No gate run under
this configuration exists yet: that a first push fills the cache and a
following push fits the deadline is an expectation, and the real push of
kwavers#1024 is its test.

Witnessed in configuration form with `cargo build --message-format=json` and
`cargo test --no-run` for `kwavers-core`: `opt_level` 1 for every named crate
in the graph, 0 for unnamed dependencies and for build scripts, and no
warning for a name absent from the build graph.

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

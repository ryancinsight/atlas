# Criterion regression gate

This Atlas-owned tool classifies phase-reversed, counterbalanced Criterion
comparisons. A candidate regression exists only when:

- the candidate-versus-baseline interval is wholly positive after the
  baseline runs first;
- the baseline-versus-candidate interval is wholly negative after the
  candidate runs first;
- both conditions hold in two retained replications;
- all four comparisons contain the same benchmark universe and complete
  change estimates; and
- every interval meets the family-wise confidence requirement.

For `m` benchmark cases, the required confidence is `1 - 0.05 / m`.
[NIST's Bonferroni inequality][nist] bounds the chance of any false regression
at 5% without assuming independent cases: each declared replicated regression
is a subset of a first-replication baseline-first interval miss, and the union
contains at most `m` such events. Criterion exposes the configured confidence
level in each [relative-change estimate][criterion-estimate] and accepts it
through [`--confidence-level`][criterion-cli].

The benchmark harness is the measurement instrument. Local measurement holds the
candidate harness constant while varying only the production code under test.
With `A` as baseline production code and `B` as candidate production code, the operator
runs two co-located `A B` pairs and two co-located `B A` pairs. Each pair stays
on one machine and materializes both revisions at the same filesystem path, so
its interval does not introduce cross-machine or checkout-identity differences.
The four pairs run within the committed local timing budget. CI only smoke-runs
benchmarks; shared-runner timings do not establish performance. The four comparison
roots are retained. Report roots do not encode runner or source-path identity, so
the operator owns and must preserve both preconditions:

```sh
confidence="$(
  cargo run --locked \
    --manifest-path <atlas>/tools/criterion-regression/Cargo.toml -- \
    required-confidence \
    --criterion-root target/criterion \
    --baseline atlas-base
)"

# Use "$confidence" for all four comparison runs. Execute two base-first and
# two candidate-first pairs, retaining each completed target/criterion tree
# under the corresponding path.

cargo run --locked \
  --manifest-path <atlas>/tools/criterion-regression/Cargo.toml -- \
  check-replicated-counterbalanced \
  --first-baseline-first-root target/criterion-first-baseline-first \
  --first-candidate-first-root target/criterion-first-candidate-first \
  --second-baseline-first-root target/criterion-second-baseline-first \
  --second-candidate-first-root target/criterion-second-candidate-first \
  --baseline atlas-base
```

Moving a completed `target/criterion` tree within the same filesystem changes
only directory metadata; build artifacts remain in the shared target
directory. Missing reports, mismatched benchmark sets, malformed estimates,
and insufficient confidence fail closed. Requiring agreement across both
orders rejects a slowdown confined to one execution order. Requiring two
pairs per order samples runner variation but does not claim immunity to
arbitrary hosted noise. The gate has no empirical percentage threshold.

## Runtime budget enforcement

Run the tool's locked Cargo verification from a configured directory outside
the Atlas development overlay, using an absolute `--manifest-path`. Cargo
discovers configuration from its working directory, as described by the
[standalone lock-resolution script](../../scripts/lockfile.py). That directory's
Cargo configuration must retain the stack's shared target directory and profile
settings without its dependency patches; do not create a second build cache.
Use absolute consumer manifest and report paths when invoking from there.

`enforce-budget` bounds how long producing benchmark results may take
(AGENTS.md `engineering_gates`: runtime budgets). By default it compiles the selected
target kind unbounded — build cost is shared-cache state, never charged to
the artifact — then executes each produced binary directly under a wall
clock, terminating it on breach and failing closed:

```sh
# Gate smoke: every bench binary runs one iteration within 60s.
cargo run --locked --manifest-path <atlas>/tools/criterion-regression/Cargo.toml -- \
  enforce-budget --manifest-path <atlas>/repos/<repo>/Cargo.toml --mode smoke

# Timing: every bench binary completes its full measurement within 300s.
cargo run --locked --manifest-path <atlas>/tools/criterion-regression/Cargo.toml -- \
  enforce-budget --manifest-path <atlas>/repos/<repo>/Cargo.toml --mode timing

# Examples: every CI-safe example completes within 60s
# (skip GPU/display-bound targets explicitly).
cargo run --locked --manifest-path <atlas>/tools/criterion-regression/Cargo.toml -- \
  enforce-budget --manifest-path <atlas>/repos/<repo>/Cargo.toml --mode examples --skip <target>

# Retained artifact: run this exact binary without rebuilding the workspace.
criterion-regression enforce-budget --manifest-path <atlas>/repos/<repo>/Cargo.toml \
  --mode timing --executable output/<experiment>/<artifact> \
  --package <package> --target <target>
```

`--executable`, `--package`, and `--target` form one selection and must be
supplied together; `--skip` applies only to compiled target selection. The
executable path resolves relative to the invoking directory before execution
changes to the metadata-resolved workspace root. Retained execution still
reads Cargo metadata, uses the selected mode's arguments and default bound,
and honors an explicit `--bound-seconds` exactly as compiled execution does.
It uses the same supervisor and shared target directory.

Smoke mode passes Criterion's `--test` argument. Custom harnesses must also
receive their repository's committed smoke configuration: Apollo's harnesses,
for example, require `APOLLO_BENCH_MODE=smoke`. The supervisor inherits the
environment; it does not infer a custom harness's mode from its target name.

The caller retains artifact provenance (source revision, build flags, and
package/target identity) and controls the counterbalanced execution order.
Selecting a retained file does not establish that it matches the current
manifest or those supplied identity labels. Keep its runtime dependencies
available and its contents unchanged through execution. Alternating retained
baseline and candidate executables requires no source or cache-artifact swap;
completed Criterion report trees still need retention between runs.

Binaries run directly rather than through `cargo` so the supervisor can
terminate and reap the benchmark itself (killing `cargo` can orphan it), with
`CARGO_TARGET_DIR` pinned to the metadata-resolved shared target so a
directly executed Criterion binary never mints a repo-local `target/`. A
breach is a defect to root-cause — oversized measurement design (fix the
instrument: flat sampling for slow iterations, geometric sweeps, smallest
regime-exercising inputs) or a genuinely slow kernel (profile and optimize
the production code) — never resolved by deleting the bench, raising the
bound in the offending diff, or skipping the smoke.

Supervision covers the immediate child, not descendants it spawns. Retained
artifacts must own their execution lifetime; this runner does not provide
process-tree containment. Operating-system supervision errors remain errors,
not evidence that the process exited or its descendants were collected.

[criterion-cli]: https://github.com/bheisler/criterion.rs/blob/0.4.0/src/lib.rs#L812-L816
[criterion-estimate]: https://github.com/bheisler/criterion.rs/blob/0.4.0/src/estimate.rs#L27-L32
[nist]: https://www.itl.nist.gov/div898/handbook/prc/section4/prc463.htm

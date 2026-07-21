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

The benchmark harness is the measurement instrument. Consumer CI holds the
candidate harness constant while varying only the production code under test.
With `A` as baseline production code and `B` as candidate production code, CI
runs two co-located `A B` pairs and two co-located `B A` pairs. Each pair stays
on one machine and materializes both revisions at the same filesystem path, so
its interval does not introduce cross-machine or checkout-identity differences.
The four pairs may run serially on one machine or as isolated jobs when the
complete instrument exceeds a finite job budget. The four comparison roots are
retained. Report roots do not encode runner or source-path identity, so consumer
CI owns and must preserve both preconditions:

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

[criterion-cli]: https://github.com/bheisler/criterion.rs/blob/0.4.0/src/lib.rs#L812-L816
[criterion-estimate]: https://github.com/bheisler/criterion.rs/blob/0.4.0/src/estimate.rs#L27-L32
[nist]: https://www.itl.nist.gov/div898/handbook/prc/section4/prc463.htm

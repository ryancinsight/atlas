# Criterion regression gate

This Atlas-owned tool classifies phase-reversed, counterbalanced Criterion
comparisons. A candidate regression exists only when:

- the candidate-versus-baseline interval is wholly positive after the
  baseline runs first;
- the baseline-versus-candidate interval is wholly negative after the
  candidate runs first;
- both conditions hold in an ABBA replication and a phase-reversed BAAB
  replication;
- all four comparisons contain the same benchmark universe and complete
  change estimates; and
- every interval meets the family-wise confidence requirement.

For `m` benchmark cases, the required confidence is `1 - 0.05 / m`.
[NIST's Bonferroni inequality][nist] bounds the chance of any false regression
at 5% without assuming independent cases: each declared replicated regression
is a subset of a first-replication baseline-first interval miss, and the union
contains at most `m` such events. Criterion exposes the configured confidence
level in each relative-change estimate and accepts it through
[`--confidence-level`][criterion].

The benchmark harness is the measurement instrument. Consumer CI holds the
candidate harness constant while varying only the production code under test.
It runs both phase-reversed replications on one machine. With `A` as baseline
production code and `B` as candidate production code, the complete schedule is
`A B B A B A A B`. Baseline and candidate each occupy positions whose sums are
18 and whose squared sums are 102, balancing their exposure to constant,
linear, and quadratic run-period terms. The four comparison roots are retained:

```sh
confidence="$(
  cargo run --locked \
    --manifest-path <atlas>/tools/criterion-regression/Cargo.toml -- \
    required-confidence \
    --criterion-root target/criterion \
    --baseline atlas-base
)"

# Use "$confidence" for all four comparison runs. Execute ABBA, then BAAB,
# retaining each completed target/criterion tree under the corresponding path.

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
and insufficient confidence fail closed. Requiring agreement across the
phase-reversed blocks rejects a slowdown confined to one run phase; it does
not claim to remove arbitrary non-polynomial runner noise. The gate has no
empirical percentage threshold.

[criterion]: https://bheisler.github.io/criterion.rs/book/user_guide/command_line_options.html
[nist]: https://www.itl.nist.gov/div898/handbook/prc/section4/prc463.htm

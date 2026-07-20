# Criterion regression gate

This Atlas-owned tool classifies counterbalanced Criterion comparisons. A
candidate regression exists only when:

- the candidate-versus-baseline interval is wholly positive after the
  baseline runs first;
- the baseline-versus-candidate interval is wholly negative after the
  candidate runs first;
- both orders contain the same benchmark universe and complete change
  estimates; and
- every interval meets the family-wise confidence requirement.

For `m` benchmark cases, the required confidence is `1 - 0.05 / m`.
[NIST's Bonferroni inequality][nist] bounds the chance of any false regression
at 5% without assuming independent cases: each declared regression is a subset
of a baseline-first interval miss, and the union contains at most `m` such
events. Criterion exposes the configured confidence level in each
relative-change estimate and accepts it through
[`--confidence-level`][criterion].

The benchmark harness is the measurement instrument. Consumer CI holds the
candidate harness constant while varying only the production code under test.
It runs both execution orders on one machine and retains the two resulting
Criterion roots:

```sh
confidence="$(
  cargo run --locked \
    --manifest-path <atlas>/tools/criterion-regression/Cargo.toml -- \
    required-confidence \
    --criterion-root target/criterion \
    --baseline atlas-base
)"

# Use "$confidence" for both comparison runs, then retain each completed
# target/criterion tree under the corresponding path.

cargo run --locked \
  --manifest-path <atlas>/tools/criterion-regression/Cargo.toml -- \
  check-counterbalanced \
  --baseline-first-root target/criterion-baseline-first \
  --candidate-first-root target/criterion-candidate-first \
  --baseline atlas-base
```

Moving a completed `target/criterion` tree within the same filesystem changes
only directory metadata; build artifacts remain in the shared target
directory. Missing reports, mismatched benchmark sets, malformed estimates,
and insufficient confidence fail closed. The gate has no empirical percentage
threshold.

[criterion]: https://bheisler.github.io/criterion.rs/book/user_guide/command_line_options.html
[nist]: https://www.itl.nist.gov/div898/handbook/prc/section4/prc463.htm

# Criterion regression gate

This Atlas-owned tool evaluates Criterion's relative median-change confidence
interval after a base/head benchmark comparison. It fails when the entire
confidence interval is above zero or when a benchmark in the named baseline
has no comparison result.

The benchmark job must run on one machine and preserve its `target/criterion`
directory:

```sh
git checkout <base-revision>
cargo bench -- --save-baseline atlas-base
git checkout <head-revision>
cargo bench -- --baseline atlas-base
cargo run --locked \
  --manifest-path <atlas>/tools/criterion-regression/Cargo.toml \
  -- check --workspace . --baseline atlas-base
```

The gate deliberately has no empirical percentage threshold. Criterion's
bootstrap confidence interval supplies the statistical decision boundary.

<a id="atlas-apollo-python-surface-2026-08-20"></a>
## ATLAS-APOLLO-PYTHON-SURFACE-2026-08-20 — Ship the typed Python surface [patch] — in-progress

The Apollo Python package currently exposes its symbols through `__init__.py`
but has no `py.typed` marker or `.pyi` surface. The active Apollo book lane is
clean and its executable-book PR is already merged; this follow-up is confined
to the repointed lane and does not touch the dirty primary checkout.

**Scope:** `crates/apollo-python/python/pyapollofft/py.typed`, the matching
stub surface, `crates/apollo-python/pyproject.toml`, and installed-wheel typing
tests. **Non-goals:** changing FFT algorithms or adding a second Python API.

**Acceptance:** the stub surface covers every re-exported binding and plan,
the package metadata declares typing-inclusive classifiers and project links,
the built wheel contains `py.typed`, and the installed-wheel test resolves the
public names with a value-semantic FFT smoke. Rust binding compute paths already
use `Python::detach` in the clean lane; any newly found heavy path must retain
that GIL-release contract.

**Owner:** current Atlas session. **Claimed files:** the clean Apollo book lane
repointed from its merged branch, the root item, and this PM record.

**Implementation:** Apollo commit `4e055407` was pushed on
`fix/apollo-python-surface` as PR
[#109](https://github.com/ryancinsight/apollo/pull/109) and merged with the
expected-head guard at default commit
`fd9ecd0206c2b4ee3993a42eec65a1703d592ac2`. Local evidence includes the
formatting, locked check, clippy, nextest, release `cp38-abi3` wheel build,
and 35 installed-wheel pytest cases. Hosted PR Rust and Python checks are
terminal-successful; `recurseml/analysis` is the existing report-only error.
Post-merge CI `32474434108` and Pages `32474432640` are queued. The dirty
primary Apollo checkout and Atlas gitlink remain unchanged until those default
runs and the live-page check are terminal. The merged clean lane and its local
branch were removed after the PR merge.


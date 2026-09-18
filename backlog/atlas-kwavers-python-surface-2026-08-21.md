<a id="atlas-kwavers-python-surface-2026-08-21"></a>
## ATLAS-KWAVERS-PYTHON-SURFACE-2026-08-21 — Complete typed and concurrent PyO3 surface [minor] — in-progress

- **Owner:** Atlas integration. **Claimed files:** `backlog.md` and
  `checklist.md`; provider source is claimed by the isolated Banach coding
  worktree for the first core-simulation vertical slice. The shared dirty
  checkout and active PR scopes remain untouched.
- **Current claim:** `crates/kwavers-python/pyproject.toml`,
  `python/pykwavers/__init__.py`, typed package artifacts, the core
  `Simulation.run` binding module and focused binding tests. The claim excludes
  open PR #439 simulated-GPU files, open PR #443 core-log files, the separate
  analysis-owned WGPU migration, and all unrelated binding families.
- **Outcome:** the Kwavers Python wheel exposes every registered Rust class and
  function through one generated, typed package surface; the wheel ships
  `py.typed` and `.pyi` files; long-running binding calls release the GIL; and
  the package facade exports exactly the registered public symbols.
- **Audit evidence:** the current registration surface contains 25 classes and
  384 top-level functions, while the facade reexports 400 extension symbols
  but omits nine registered functions and four imported symbols from
  `__all__`. No `py.typed` or `.pyi` files exist. Static inspection identifies
  synchronous solver, thermal, GPU-session, bubble, cavitation-monitor, and
  chirp/sweep paths that still hold the GIL. Evidence source: the independent
  Kwavers binding audit at `crates/kwavers-python/src/lib.rs`,
  `python/pykwavers/__init__.py`, and the affected binding modules.
- **Acceptance:** a deterministic Rust registration-driven generator emits
  real signatures, defaults, classes, properties, NumPy arrays, optionals,
  tuples, mappings, and metadata without `Any`/ellipsis placeholders; CI
  regenerates and diffs the stubs; the installed wheel contains the extension,
  package facade, stubs, and marker; a strict typed consumer passes; an
  independent Python-thread regression proves each migrated long-running call
  releases the GIL while returned values remain correct; and the runtime
  inventory has no missing or extra public exports. Run the affected locked
  Rust gates, Python tests, doctests, Rustdoc, and wheel smoke at one exact
  provider head.
- **Sequencing:** first land the generator and exact registration inventory,
  then migrate one complete `Simulation::run` slice with the concurrency
  oracle, followed by thermal, GPU-session, bubble, monitor, and chirp families
  as separate vertical increments. Do not hand-author a partial stub or claim
  GIL coverage from static `.detach` counts alone.
- **Non-goals:** no domain logic in Python, no runtime introspection as the
  source of truth, no facade compatibility aliases, and no unrelated solver
  redesign.
- **First vertical slice:** isolated commit
  `db49f2f09cba6b24381156a8404cd08942a44f52` adds the typed package marker and
  stubs, releases the GIL around the core `Simulation.run` computation, and
  adds value-sensitive Python binding/thread-pool tests. The test oracle does
  not claim overlap or GIL proof; `py.detach` at the binding boundary is the
  static GIL-release evidence. Focused Rust,
  Nextest (21/21), Python (4/4), abi3 wheel, install, and smoke checks pass.
  PR [#590](https://github.com/ryancinsight/kwavers/pull/590) was opened at
  that head; strict mypy/Ruff/Black are unavailable and locked Cargo gates are
  blocked by the inherited Atlas overlay re-resolving the lockfile.
- The test-oracle correction is commit
  `124ef839e27aba71a8f3749c33acaf7d0ae1ee93`, now the PR head. Its focused
  Rust and wheel-backed tests pass; the previously collected hosted run set
  at `db49f2f09cba...` is stale and must not be attributed to the corrected
  head.
- **Hosted hold at the superseded head:** PR #590 was mergeable but `unstable`; CI/CD
  `32492642895`, legacy audit `32492642913`, Python wheel smoke
  `32492642908`, architecture validation `32492642942`, and Deploy mdBook
  `32492643372` remain queued. `recurseml/analysis` is errored and CodeRabbit
  is rate-limited. The live Pages site is reachable but older than the PR and
  is not evidence for either head; fresh checks for `124ef839e27a...` are
  required. No pointer advance or bypass is used.
- **Type-mapping increment (commit `60e871bad`, new PR #590 head):** every
  duck-typed `Bound<'_, PyAny>` parameter resolves through an audited
  `DUCK_TYPES` table keyed by `(class, function, parameter)` with per-entry
  extraction-code provenance; unaudited PyAny parameters fail the generator
  closed instead of emitting bare `object`. The stub honors
  `#[pyfunction(name = ...)]` renames (recovering the previously missing
  `run_standing_wave_suppression`), escapes Python keyword parameters
  PyO3-style (`lambda` -> `lambda_`), and types string-keyed result dicts as
  `Dict[str, object]` (422/422 literal-key `set_item` sites verified).
  Zero bare `object` parameters remain; an AST guard test enforces the
  invariant and the strict typed-consumer fixture exercises each mapped
  union. Focused suite 23 passed / 1 skipped with a freshly built abi3 wheel
  (`kwavers_python-0.1.0-cp38-abi3-win_amd64.whl`) installed. Pre-existing
  finding recorded, not caused by this increment:
  `get_array_weighted_mask` returns all zeros for annular elements at lane
  head `124ef839e27a` (`test_kwave_array_per_element_superposition_reduces_to_shared_signal`
  fails against the freshly built extension); the Rust binding needs its own
  defect increment. All prior hosted evidence is stale at the new head.
- **Annular-mask finding resolved (commit `38b54ce82`, PR #590 head):** not a
  Rust defect. Bowl/annulus surfaces lie one radius from `position` (the
  focus), matching k-wave-python; the test had placed the focus mid-grid with
  R = 10 mm on a 14.4 mm grid so the cap fell outside the domain and the BLI
  horizon correctly rejected every sample. Test now places the focus one
  radius past mid-grid and asserts both annuli contribute disjoint radial
  bands. Also fixed in-test: "Rectangular" → canonical "Uniform" alias
  round-trip expectation in `test_transducer_array.py`. Full local suite
  triage (898 passed / 90 failed / 62 skipped): remaining failures are
  environmental (missing external k-wave example utils, long-physics
  timeouts), no regressions from this lane.
- **Continuation refinements (uncommitted at `60e871bad`, part of this
  increment):** the generated stubs now pass mypy `--strict` — array aliases
  are `TypeAlias`-annotated, `__init__` returns `None` (PEP 484), and
  `__eq__` takes `other: object` (Liskov); the facade stub splits the eight
  `kwave_parity` helpers from the extension import and declares
  `__author__`/`__version__`. CI wiring: a `python-surface` job in `ci.yml`
  runs `tools/generate_surface.py --check` (regen-and-diff gate) plus the
  generator/typed-consumer tests with mypy installed; the wheel-smoke
  `kwave-comparison` job runs the runtime export-inventory oracle against the
  installed wheel (`KWAVERS_PYTHON_PACKAGE=installed`). The tracked abi3
  `.whl` build artifact is removed from git. Local gates: `--check` passes,
  generator staleness / typed-consumer / runtime-inventory tests pass (21
  passed, 3 skipped in source mode; runtime oracle 16/16 against the installed
  wheel).
- **Thermal GIL family (lane rebased onto `origin/main` `377a98c86`):**
  `ThermalSimulation::run` now runs its entire diffusion time loop inside
  `py.detach`, mirroring the `Simulation::run` contract (GIL-phase setup /
  owned-Rust-data time loop / GIL-phase PyArray assembly). Added the runtime
  overlap oracle `test_thermal_simulation_run_releases_gil_with_returned_value_correctness`
  on `test_bindings_surface.py`: a 48³ grid with a constant heat source holds
  a solve window well past the 0.5 s floor while the main thread exceeds 1M
  pure-Python GIL increments; returned-value correctness shows bit-identical
  temperature fields for identical inputs and a doubled heat source raises the
  temperature rise by exactly 2× (linear diffusion, ratio 1.0 within 1e-6).
  Wheel-backed: 16 passed / 1 skipped in `test_bindings_surface.py`; fmt,
  clippy `-D warnings`, nextest 21/21 clean. The `Simulation::run` slice
  (PR #590) and the WGPU provider migration (PR #602) are both completed;
  thermal is the first of the remaining GIL families (thermal, GPU-session,
  bubble, monitor, chirp).
- **Bubble ODE GIL family (same lane, next vertical increment):**
  `solve_rayleigh_plesset`, `solve_keller_miksis` (and the Keller–Herring
  delegation), `solve_gilmore`, and `solve_hodgkin_huxley_like` now run their
  RK4 / ODE integration compute inside `py.detach`, mirroring the
  `Simulation::run` / thermal contract. Added the runtime overlap oracle
  `test_bubble_ode_releases_gil_with_returned_value_correctness`: a 10M-step
  `solve_keller_miksis` holds a ~1s solve window while the main thread exceeds
  1M pure-Python GIL increments; returned-value correctness shows bit-identical
  outputs for identical inputs and a doubled driving amplitude swings the wall
  strictly farther (higher max / lower min radius). Wheel-backed: 17 passed /
  1 skipped in `test_bindings_surface.py`; fmt, clippy `-D warnings`, nextest
  21/21, generator `--check` clean.
- **Published at the rebased lane head (2026-08-22):** the lane (rebased onto
  `origin/main` `377a98c86`, carrying the thermal and bubble-ODE GIL
  increments) force-published to PR #590 with a lease guard against the
  superseded head `6616c904`; PR head is now `a2a3878b` and `MERGEABLE`.
  Hosted runs are executing rather than queued: Python wheel smoke
  `32588842603` and Legacy Migration Audit `32588842587` in progress, CI/CD
  `32588842609` and Deploy mdBook `32588842869` queued. All prior hosted
  evidence remains stale; merge only at exact head after terminal required
  checks.
- **Collection and blocker fix (2026-08-23):** wheel smoke, Legacy Migration
  Audit, and Deploy mdBook are terminal success; CI/CD Pipeline failed on its
  `Python Typed Surface` job: the crate's declared pytest addopts pass
  `--timeout/--benchmark-disable`, whose plugins (pytest-timeout,
  pytest-benchmark) the job did not install. Head `d1281f990` installs both
  declared dependencies; replacement runs pending.
- **Closed (2026-08-23):** replacement run set at `d1281f990` terminal:
  CI/CD Pipeline (incl. Python Typed Surface), Python wheel smoke, Deploy
  mdBook, and Legacy Migration Audit all success. The only failing check is
  Architecture Validation — the pre-existing repo-wide defect filed below,
  failing identically on every PR head, not required by any branch
  protection. PR [#590](https://github.com/ryancinsight/kwavers/pull/590)
  merged with the expected-head guard at default `ca5c9c93`; post-merge
  default runs in progress before any Atlas gitlink advance.
  **Not this PR's regression:** the Architecture Validation job fails on every
  open PR head across the repository (12 consecutive failures on unrelated
  branches, main's own post-merge runs cancelled with no terminal baseline).
  Local reproduction attributes it to ~2,850 warnings across 103
  example/test/bench files under `-D warnings --all-targets` — a ratchet-scale
  burn-down filed below as its own item.


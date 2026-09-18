<a id="atlas-kwavers-python-gil-2026-08-21"></a>
## ATLAS-KWAVERS-PYTHON-GIL-2026-08-21 — Detach Simulation.run [minor] — in-progress

- `Simulation::run` now accepts the hidden PyO3 `Python<'_>` token, clones the
  backend-neutral grid/medium/config inputs, and executes `SimulationRunner::run`
  inside `py.detach`. The detached closure captures no pyclass or Python handle.
- Added `tests/test_simulation_gil.py`, an event-based Python-thread regression
  that requires concurrent Python progress and verifies the returned result's
  time-step count, sensor shape, and finite values.
- Provider `cargo check -p kwavers-python --lib` passes. The full provider
  formatter remains blocked by pre-existing peer-owned formatting drift in
  `kwavers-medium/src/absorption/stokes.rs`; no unrelated formatting was
  applied. Native wheel/runtime execution remains pending until a built
  extension is available.


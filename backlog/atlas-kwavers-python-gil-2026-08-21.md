<a id="atlas-kwavers-python-gil-2026-08-21"></a>
## ATLAS-KWAVERS-PYTHON-GIL-2026-08-21 — Detach Simulation.run [minor] — todo
- `Simulation::run` executes `SimulationRunner::run` inside `py.detach` (`crates/kwavers-python/src/simulation_py/run/execute.rs`; landed in 0ff20ac2f, an ancestor of kwavers origin/main). The detached closure captures no pyclass or Python handle.
- Oracle: `test_simulation_run_releases_gil_with_returned_value_correctness` in `crates/kwavers-python/tests/test_bindings_surface.py` (spinner-thread overlap, bit-identical repeat, amplitude linearity). basis: 2b000c51b; only `python-release.yml` (`python-test-path: crates/kwavers-python/tests`) runs that file, and the PR wheel smoke job names other files. next: add it to the wheel smoke job.

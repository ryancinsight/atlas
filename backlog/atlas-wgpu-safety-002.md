<a id="atlas-wgpu-safety-002"></a>
## ATLAS-WGPU-SAFETY-002 — Specify the fallible WGPU layout/dispatch boundary [arch] — todo
- **outcome:** the WGPU buffer-layout and dispatch boundary returns typed `Result`s instead of panicking/asserting on adapter or layout mismatch, across CPU/CUDA/WGPU callers of the shared `ComputeBackend` seam.
- **next:** migrate the first complete operation family through the typed error seam; verify CPU/CUDA/WGPU callers against it before extending to further families.
- **Acceptance:** the migrated family's adversarial/boundary tests assert the typed error, not a panic; unaffected families are untouched.
- Owner: unclaimed; scope spans Hephaestus/Coeus WGPU backends.

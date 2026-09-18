<a id="atlas-coeus-nlls-004"></a>
## ATLAS-COEUS-NLLS-004 — original specification — todo

- **Evidence of gap**: `coeus-optim` ships `SGD`, `Adam`, `AdamW`, `RMSProp`,
  and `Adagrad` only — all first-order stochastic, sized for network training.
- **Why it blocks**: per-voxel diffusion fitting is millions of independent
  small dense residual problems. A damped Gauss-Newton step with an analytic
  Jacobian converges in single-digit iterations; a first-order stochastic
  optimizer is the wrong instrument by orders of magnitude. Log-linear DTI is
  unaffected — it routes through `leto-ops` (`pinv`, `qr_decompose`,
  `cholesky_solve`), which already exist.
- **Blocks**: DKI, NODDI, IVIM, free-water, and every other nonlinear model.
- **Acceptance**: batched over a leading problem axis; verified against an
  analytical oracle with a known minimum and against a published test problem
  set; convergence criterion is a derived relative-residual bound, never a fixed
  iteration count.
- **Class**: `[minor]`, repository `repos/coeus`.


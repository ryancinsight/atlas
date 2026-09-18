<a id="atlas-coeus-nlls-004"></a>
## ATLAS-COEUS-NLLS-004 — original specification — todo

outcome: `coeus-optim` gains a damped Gauss-Newton (or equivalent second-order) nonlinear least-squares optimizer batched over a leading problem axis, for per-voxel diffusion fitting (millions of independent small dense residual problems) where first-order stochastic optimizers (`SGD`, `Adam`, `AdamW`, `RMSProp`, `Adagrad` — all it currently ships) are the wrong instrument by orders of magnitude. Log-linear DTI is unaffected (already routes through `leto-ops`).

blocks: DKI, NODDI, IVIM, free-water, and every other nonlinear diffusion model.

acceptance: verified against an analytical oracle with a known minimum and against a published test problem set; convergence criterion is a derived relative-residual bound, never a fixed iteration count.

Class: `[minor]`, repository `repos/coeus`.

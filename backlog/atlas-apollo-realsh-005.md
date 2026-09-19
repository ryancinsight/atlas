<a id="atlas-apollo-realsh-005"></a>
## ATLAS-APOLLO-REALSH-005 — original specification — todo

outcome: Apollo implements the real, even-order, antipodally symmetric spherical-harmonic basis, a design matrix over a scattered direction set, and Laplace-Beltrami regularization, owned in Apollo per ADR 0036 decision 2 (a RITK-local path would fork the SH normalization dimension).

next: declare one basis convention (Descoteaux vs Tournier ordering/normalization) and pin it with a reference-case test against published coefficients; implement the design matrix and regularization in `repos/apollo` (pointwise SH eval already exists at `infrastructure/kernel/spherical_harmonic.rs:234`).

Blocks: every ODF/FOD model in `ritk-diffusion`. Class: [minor], repo `repos/apollo`.

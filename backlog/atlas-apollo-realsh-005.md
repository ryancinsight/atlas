<a id="atlas-apollo-realsh-005"></a>
## ATLAS-APOLLO-REALSH-005 — original specification — todo

- **Evidence of gap**: `apollo-sht` owns complex SH on Gauss-Legendre product
  grids. `infrastructure/kernel/spherical_harmonic.rs:234` exposes
  `spherical_harmonic(degree, order, theta, phi) -> Complex64`, so pointwise
  evaluation at an arbitrary direction already exists; the real, even-order,
  antipodally symmetric basis, the design matrix over a scattered direction set,
  and Laplace-Beltrami regularization do not.
- **Why Apollo and not RITK**: Apollo owns the transform bounded context. A
  RITK-local associated-Legendre or normalization path forks the SH dimension
  and is the exact failure mode ADR 0036 decision 2 exists to prevent.
- **Convention pinning**: the basis has several published orderings and
  normalizations (Descoteaux and Tournier differ). The implementation declares
  one, and a reference-case test asserts it against published coefficients.
- **Blocks**: every ODF/FOD model in `ritk-diffusion`.
- **Class**: `[minor]`, repository `repos/apollo`.


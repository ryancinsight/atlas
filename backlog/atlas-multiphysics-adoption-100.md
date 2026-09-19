<a id="atlas-multiphysics-adoption-100"></a>
## ATLAS-MULTIPHYSICS-ADOPTION-100 — CFDrs/Kwavers/Helios provider adoption and suite closure [major] [arch] — in-progress

outcome: CFDrs, Kwavers, and Helios directly adopt their 22 named providers (no wrapper/fallback), the stack overlay/lock/registry checks pass, and each integrator's book/Pages evidence is terminal — verified by analytical or differential oracles, never a green build alone.

Dependency-ordered next steps: (1) migrate CFDrs to Harmonia's typed field exchange, deleting its Aitken/relaxation wrapper; (2) give Kwavers a reproducible IVP parity gate with fresh k-wave-python oracle provenance (its comparator currently falls back/truncates and ignores CFL in one path); (3) harden Helios's DICOM/HDF5 dimension and resource-allocation boundaries; (4) complete PyO3 GIL-release, input-validation, and typing/wheel evidence (CFDrs has no GIL-release site); (5) rerun the full exact-head, overlay, lock, book, figure, performance, and hosted Pages acceptance oracle.

Depends on: `ATLAS-CONFORMANCE-BENCH-099`, `ATLAS-PUBLISH-001-BOOK-MDBOOK-TEST-001`, `ATLAS-OVERLAY-005` (`ATLAS-COEUS-LINT-RATCHET-097` closed — found already merged upstream).

History of provider-by-provider closures (Consus, Leto, CFDrs conformance; Mnemosyne, Helios DICOM, Kwavers FDTD/GPU-ownership, CFDrs backward-step/Fourier/SSOR) lives in git history and provider-local boards, not this item.

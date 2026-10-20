<a id="atlas-release-publish-identity"></a>
## ATLAS-RELEASE-PUBLISH-IDENTITY — Verify duplicate release publication [patch] — private review
- Owner: isolated release-identity lane; baseline `b553c42da72dcdeb2bb2644c60759dc465fb329a`; pending/SemVer owner paths remain excluded.
- Defect: after validation, an already published exact version still requests OIDC and uploads unconditionally; version-only suppression cannot establish source identity.
- Correction: fresh Cargo verification, committed source/HEAD/path and complete archive identity; strict API/index/download agreement; explicit complete decision before both existing conditionals.
- [x] Reproduce baseline unconditional-auth wiring; exercise real Cargo/Git package and registry boundary cases.
- [ ] Complete exact-head gates, independent review and real registry-artifact verification; private evidence is external.
- Public actions, credentials/settings, permissions, current validation and claimed owner work remain unchanged. See [design](../docs/pr/crate-release-identity.md).

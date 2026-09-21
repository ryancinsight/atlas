# ADR 0063: Shared raster codec ownership

- Status: Accepted
- Date: 2026-09-20
- Item: [ATLAS-RASTER-001](../../backlog.md#ATLAS-RASTER-001)

## Decision

Consus owns `consus-raster`, the shared JPEG byte decoder and bounded EXIF
interpreter consumed by Metis and RITK. It remains separate from Consus's
exact-roundtrip compression trait because JPEG DCT encoding is lossy.

RITK previously supplied first-party sequential and lossless JPEG computation.
Metis's progressive JPEG and EXIF addition exposed overlapping format work.
The migration combines those capabilities upstream; it does not replace a
first-party implementation with a parallel third-party decoder. Integer sample
precision is preserved at the provider boundary. EXIF orientation is metadata,
never an implicit clinical geometry transformation.

```text
Metis scoped bytes and raster presentation --> consus-raster
RITK medical sample conversion             --> consus-raster
RITK viewer                               --> Metis
```

Direct Metis-to-RITK reuse would create a repository dependency cycle. Iris
excludes formats under [ADR 0029](0029-iris-visualization-promotion.md).
A separate repository is unnecessary because
Consus already owns formats and compression without depending on either
consumer. Clinical formats, DICOM metadata and modality interpretation stay
in RITK; UI permissions, path traversal defenses and placement stay in Metis.

## Migration and evidence

[Consus](../../repos/consus/backlog.md#CONSUS-RASTER-001) implements bounded
sequential, progressive and lossless JPEG decoding and shared EXIF parsing.
[RITK](../../repos/ritk/backlog.md#RITK-JPEG-001) preserves medical conversion
and file I/O while deleting superseded format computation.
[Metis](../../repos/metis/backlog.md#METIS-ASSETS-001) consumes integer pixels,
normalizes display orientation once and repeats native V06 capture.

Completion requires provider and consumer gates, exact lossless values,
independent progressive and orientation fixtures, malformed and resource-limit
rejections, and removal of duplicate decoders. The dependency graph must remain
acyclic. Source review establishes the ownership decision; it does not establish
the decoder's behavior or native display correctness.

Consumer gates resolve committed Git sources outside the local stack overlay.
Concurrent member pre-push hooks currently snapshot and restore the same lockfile
without serialization; one can restore another hook's temporary overlay state.
After such contention, verify the committed lock separately before accepting a
consumer result. Hook serialization remains an integration-tooling requirement.

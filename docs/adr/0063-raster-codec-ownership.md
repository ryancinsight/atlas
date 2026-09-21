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
consus-raster                             --> apollo-dctdst-core --> eunomia
```

Direct Metis-to-RITK reuse would create a repository dependency cycle. Iris
excludes formats under [ADR 0029](0029-iris-visualization-promotion.md).
A separate repository is unnecessary because
Consus already owns formats and compression without depending on either
consumer. Clinical formats, DICOM metadata and modality interpretation stay
in RITK; UI permissions, path traversal defenses and placement stay in Metis.

Revision 2026-09-21: Consus retains JPEG entropy parsing, dequantization, sample
reconstruction and color conversion. Apollo owns reusable DCT-III mathematics
through `apollo-dctdst-core`, which does not import the FFT or execution stack.
The fixed-capacity plan serves the separable JPEG inverse transform. Existing
Apollo callers migrate to that same implementation under
[Apollo ADR 0069](../../repos/apollo/docs/adr/0069-lightweight-direct-dct-kernel.md)
and [PR 526](https://github.com/ryancinsight/apollo/pull/526).

Consus also owns the opt-in `DecodedImage::display_samples` iterator because
sample packing and encoded precision define the same full-range integer mapping
in both consumers. It preserves encoded-grid channel order and raw storage.
Metis chooses that mapping before alpha and orientation handling; RITK's JPEG
volume reader chooses it before luminance conversion. Medical codec consumers
retain raw samples for signed interpretation, modality rescaling and windowing.

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
A consumer result binds to its committed lockfile. Verification that temporarily
changes that file must exclude concurrent writers.

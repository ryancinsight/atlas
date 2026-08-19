# ADR 0045 — Native HTTP/S3 transport stack (moirai transport, consus S3)

- Status: Accepted
- Date: 2026-06-02
- Revised: 2026-08-18 (relocated from `repos/moirai/docs/adr.md`; status
  Proposed → Accepted; delivery state recorded — see *Revision note*)
- Driver: backlog ATLAS-CONSUS-ADR015-076
- Supersedes: `repos/moirai/docs/adr.md` §"ADR-015: Native HTTP/S3 Transport
  Stack (Tokio-Free Object Storage)", which is now a pointer to this record.

This is a **cross-repo contract** between `moirai` (generic transport) and
`consus` (S3 protocol and storage surface), which is why it lives in the
meta-repo rather than in either member. Member-side citations refer to it as
"atlas ADR-0045"; the historical in-tree citations say "ADR-015" and are being
repointed here.

## Context

consus's `s3` feature is the last hard Tokio coupling across the atlas repos.
The legacy `S3Reader` (`consus-io` `io/async_io/s3.rs`) drives `rusoto_s3` +
`reqwest`, both wired to Tokio's concrete reactor types and not
runtime-swappable. consus's async *format* layer (`AsyncReadAt`-generic HDF5
parsers) is already runtime-agnostic and Moirai-drivable via `Moirai::block_on`.
Only the network transport remains coupled.

Per moirai ADR-014 / ADR-006(async) / ADR-013, Moirai already provides,
reactor-backed and value-tested:

- `moirai-pal::net` — async `AsyncTcpStream`/`AsyncTcpListener` over
  epoll/kqueue/IOCP with waker registration and no-active-reactor self-wake.
- `moirai-async::{net,io,fs}` — `AsyncRead`/`AsyncWrite`/`AsyncBufRead`,
  `spawn_blocking`, cancellation and backpressure contracts, `Moirai::block_on`.

The gap is therefore only the three layers above the socket: TLS, HTTP/1.1, and
the S3 surface.

## Decision

Split the work along the stack's `communication = moirai` /
`datatype-and-store = consus` boundary. **Moirai ships store-agnostic transport
only and never learns what S3 or AWS is**; the S3 protocol — a vendor-specific
storage-addressing concern — lives in consus on top of Moirai's HTTP. Reuse
audited sans-I/O libraries for all cryptography and parsing; build only the I/O
orchestration glue each side must own.

**In moirai** (generic communication, over the existing `moirai-net` sockets):

1. `moirai-tls` — TLS 1.2/1.3 client sessions driving the `rustls` state machine
   over a `moirai-async` `AsyncTcpStream`. No hand-rolled cryptography.
2. `moirai-http` — HTTP/1.1 client over `moirai-tls`/`moirai-net`, reusing the
   `http` and `httparse` crates. Owns request serialization, response-body
   framing (Content-Length + chunked), bounded keep-alive pooling, redirect
   handling, and per-request deadlines. HTTP/2 out of scope. **This is moirai's
   S3-facing boundary — it knows HTTP, not S3.**

**In consus** (storage backend, NOT in moirai):

3. A consus S3 client rebuilt on `moirai-http` instead of `rusoto_s3` +
   `reqwest`, owning the vendor-specific parts: SigV4 signing,
   `GetObject(Range)` + `HeadObject`, bucket/key addressing, credential
   resolution, and S3 error-XML decoding. Surfaces an `AsyncReadAt` implementor
   in place of the rusoto `S3Reader`. Keeping SigV4 out of moirai preserves
   moirai as a pure, AWS-agnostic communication library.

### Reuse-vs-build

- Reuse in moirai: `rustls` + roots, `http`, `httparse`, `socket2`.
- Reuse in consus: SigV4 signing and XML parsing. These AWS/XML dependencies do
  **not** enter moirai's tree.
- Build in moirai: the TLS↔socket pump; HTTP connection lifecycle, pool, chunked
  codec, timeouts.
- Build in consus: S3 request assembly/signing over `moirai-http`, plus the
  `AsyncReadAt` adapter.

Hand-rolling TLS is prohibited.

### Execution-model alignment

All three layers are async-domain → `moirai-async` (AsyncPolicy), never
`moirai-parallel`; this preserves the parallel≠concurrent split. Pure consus
format logic stays synchronous (async-contagion prohibition); only the
byte-source boundary is async.

### Alternatives rejected

1. **Reimplement TLS/crypto from scratch** — security-critical, no value over
   `rustls`.
2. **Fork reqwest/hyper onto moirai I/O** — hyper is deeply Tokio-coupled; fork
   maintenance unbounded.
3. **Embed a current-thread Tokio runtime on a moirai worker to host reqwest** —
   rejected as the goal (still ships Tokio), retained as the documented fallback
   so consus is never blocked.
4. **Layered sans-I/O-glue stack over the existing reactor** — SELECTED.

## Phasing

- **P0** [arch]: this ADR + a spike proving moirai-net loopback echo and a
  rustls handshake over loopback on Linux **and** Windows.
- **P1** [minor, moirai]: `moirai-tls`.
- **P2** [minor, moirai]: `moirai-http`. Moirai's deliverable ends here.
- **P3** [minor, consus]: consus S3 client on `moirai-http` behind a feature
  alongside the legacy rusoto backend; both green on MinIO.
- **P4** [minor, consus]: comparative benchmark recorded (consus S3 on
  `moirai-http` vs `rusoto_s3`).
- **P5** [major, consus]: flip the consus default to the native backend; demote
  rusoto/reqwest to legacy/optional; remove Tokio from consus's production tree.

## Revision note — 2026-08-18

Two changes, both recording facts rather than altering the decision.

**Relocated.** The record was written in `repos/moirai/docs/adr.md`, but it
decides work in two repositories. Governance places a cross-repo contract in the
meta-repo, with member items citing upward. moirai's copy is now a pointer.

**Status Proposed → Accepted.** The record read
`Proposed (requires sign-off before P1 implementation)` while P1–P3 were
demonstrably built and merged in both repos. A Proposed ADR governing landed
code is a governance defect; Accepted is what the tree already reflects.

Accepted records the decision's adoption, **not** completion of its phases. As
built on 2026-08-18 the phases stand as follows. Each claim below is grounded in
a tree artifact; where the tree does not settle a question this note says so
rather than asserting.

| Phase | State | Evidence |
| --- | --- | --- |
| P0 | Partial — Linux leg evidenced, Windows leg unverified | `moirai/moirai/tests/net_reactor_spike.rs`; `moirai/moirai-tls/tests/handshake.rs`. `moirai/.github/workflows/rust-ci.yml` runs `ubuntu-latest` only, so the ADR's "Linux **and** Windows" exit gate is not verifiable from the tree. |
| P1 | Delivered, narrower than specified | `moirai/moirai-tls/` exists, `#![forbid(unsafe_code)]`, 2 tests (trusted round-trip, untrusted-root fail-closed). It depends on `futures-rustls` and delegates the byte pump to it rather than moirai owning the `read_tls`/`write_tls` loop as the Decision text describes. Expired-cert and wrong-hostname tests, and the differential against `tokio-rustls`, are absent. |
| P2 | Delivered, two deliverables missing | `moirai/moirai-http/` with `codec.rs` (httparse head parse, Content-Length and chunked bodies), bounded keep-alive pool, per-request deadline via `moirai_async::timer::timeout`; 9 tests. **Redirect handling is not implemented**, and no idle-eviction timer was found. |
| P3 | Delivered, with recorded gaps | `consus/crates/consus-io/src/io/async_io/s3_moirai/` (`client.rs`, `sigv4.rs`) — GET/PUT/DELETE/HEAD/ListObjectsV2, `quick-xml` decoding with allocation budgets, 404 → typed `Error::NotFound`. SigV4 carries an AWS-published known-answer test. `consus/crates/consus-zarr/src/store/s3_moirai.rs` provides `S3MoiraiStore`. Gaps: credential resolution from environment and `~/.aws/credentials` is not implemented (`S3Config` takes bare `String` keys); region/endpoint/bucket are `String`, not the validating newtypes this ADR required; `consus-hdf5`'s async tests still use `#[tokio::test]` (11 of them). |
| P4 | Implementation delivered; hosted measurement collected | `consus/crates/consus-zarr/benches/s3_rusoto_moirai.rs` adds a Criterion comparison of identical ranged reads through `S3MoiraiReader` and `S3Reader`; the `s3-minio` CI job runs it against a deterministic 1 MiB object and uploads `target/criterion/s3_range_read`. The standalone lock repair reports `consus/Cargo.lock: HEAD ok / worktree ok`; isolated locked compilation of the benchmark passes outside the Atlas overlay, and the in-process differential passes 2/2. Hosted run `32178624452` at Consus commit `d15bf793cb4dd86bbb53b966ea5ce2884dd8cab0` is the authoritative comparative result. Its MinIO job passed, uploaded artifact `9340113561`, and the committed 1 MiB / 256 KiB cell measured native median `862,063.015 ns` versus legacy median `828,983.683 ns`, or `0.9616` native/legacy throughput at the `0.9000` threshold. The artifact is available at [the hosted Criterion report](https://github.com/ryancinsight/consus/actions/runs/32178624452/artifacts/9340113561). |
| P5 | Rejected for Consus package integration; next-breaking-release removal prepared | The current 0.1 feature contract remains unchanged: `s3` is legacy Rusoto and `s3-moirai` is native; neither is a default feature. The next breaking release may make native S3 the default only after the P5 gates below pass. |

Two naming facts worth recording, because they make the phase text read as
inaccurate against the tree:

- The legacy feature is named **`s3`**, not `s3-tokio` as the phasing text says;
  the native one is `s3-moirai`.
- Because neither backend is a default, P5's "flip the default" has no default
  to flip in the current feature shape. P5 needs respecification before it can
  be executed, not merely implementation.

**P4 implementation note — 2026-08-18.** The benchmark is intentionally
hosted-only: it uploads one deterministic object outside the measured region,
validates its length, then measures the same byte range through both readers.
The existing in-process differential remains the value-semantic oracle; the
Criterion report is performance evidence, not a correctness substitute.

**P5-A baseline measurement — 2026-08-18.** Hosted run `32178624452` at
Consus commit `d15bf793cb4dd86bbb53b966ea5ce2884dd8cab0` passed the MinIO
correctness lane, the Criterion benchmark, and the 90% parser gate. The pinned
MinIO image is
`minio/minio@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e`
on `ubuntu-latest`, with static workflow credentials (`minioadmin`) and the
stable Rust toolchain. For the committed 1 MiB object / 256 KiB range cell,
native median was `862,063.015 ns`, legacy median was `828,983.683 ns`, and
native/legacy throughput was `0.9616` against the `0.9000` threshold. The raw
Criterion artifact is `9340113561` ([download](https://github.com/ryancinsight/consus/actions/runs/32178624452/artifacts/9340113561)).

This is one of the P5-A cells, not the whole qualification: the two additional
object/range sizes required below have not yet been run. The result therefore
supports no default flip by itself, but it does replace the prior "no measured
result" state with a passing baseline and a reproducible hosted gate.

P5 is now a staged decision rather than one undifferentiated change:

1. **P5-A — qualification.** Run the committed benchmark against the pinned
   MinIO image on the same runner for the committed 1 MiB object / 256 KiB
   range case and at least two additional object/range sizes. Record the full
   Criterion artifact, runner/toolchain, MinIO image digest, and credentials
   mode. The existing differential and live MinIO byte checks must pass in the
   same workflow.

**Baseline result.** The committed 1 MiB / 256 KiB cell passed at `0.9616` in
hosted run `32178624452`; the parser selected Criterion's `new/estimates.json`
reports and retained the raw artifact. The two additional P5-A cells remain
outstanding.

**P5 product decision — 2026-08-18.** The performance gate passed, but the
package boundary decision is not to make Consus packages connect to third-party
online storage. Accordingly, the next breaking release does **not** promote
native S3, retain a legacy S3 compatibility path, or ship either backend as an
optional package feature. The release-preparation branch removes the S3
modules, Rusoto/Reqwest/Moirai-HTTP S3 dependencies, package-facing S3 APIs,
and MinIO benchmark workflow from `consus-io` and `consus-zarr`. Applications
that need online object storage must own that integration outside these
packages, using Consus' local/filesystem or abstract I/O surfaces as the
boundary. P5-A's hosted result remains historical performance evidence; it is
not an adoption authorization.

**Async ownership correction — 2026-08-18.** The release-preparation Consus
branch also removes the Consus-owned `async-io`/`async-traits` surface and its
Tokio test executor. Async HDF5 parsing now consumes Moirai's native
`moirai_async::io::{AsyncReadAt, AsyncLength}` contracts and executor; the
positioned contracts and in-memory reader belong to `moirai-async`, not
`consus-io`. The provider API is locally verified but still requires a Moirai
provider revision before the Consus Git dependency can be published and locked
at a hosted commit.

2. **P5-B — package boundary in the next breaking release.** Do not add an
   S3 default or optional feature to the Consus packages. Remove the legacy and
   native S3 implementations and their production dependency trees; keep
   network/object-storage clients in an application-owned integration layer.
3. **P5-C — external migration.** Downstream applications that currently use
   `s3` or `s3-moirai` must move those clients out of Consus before the breaking
   release. There is no in-package compatibility window because the explicit
   product requirement is that Consus packages never connect to third-party
   online storage.

If any P5-A cell misses the 90% threshold or the correctness gate fails, the
performance evidence is incomplete; the threshold, workload, and assertions are
not lowered. In either case, the product decision above still prohibits an S3
package integration. The next release action is downstream migration to an
application-owned storage adapter, not a default switch.

The moirai-side implementation checklist at
`repos/moirai/docs/adr-015-checklist.md` is **not** reliable evidence: its header
claims "P0–P4 done; P5 partial" while every checkbox in the document is
unchecked, and the commit it cites for P0 (`bcf3ed1`) is in fact
`fix(moirai-http): include non-default port in Host header`. Reconciling or
retiring that checklist is follow-up work, not part of this record.

## Consequences

- moirai gains two crates on its public surface and, by this ADR's boundary,
  never gains an AWS dependency.
- consus carries two S3 backends until P5 closes. The `#[expect(dead_code)]`
  annotations on the legacy rusoto error surface in
  `consus-zarr/src/store/s3.rs` are scoped to that removal and expire on their
  own when it lands.
- `moirai-tls` selects a `moirai-crypto` rustls `CryptoProvider` rather than
  `ring`/`aws-lc-rs`. This ADR did not contemplate that substitution; whether
  that provider carries adequate assurance for a TLS client is an open question
  recorded here, not answered.

## Verification

- `moirai-tls`: loopback handshake against a rustls server; adversarial
  cert-validation fail-closed tests. Delivered in part — see the revision note.
- `moirai-http`: local HTTP/1.1 server; framing and pool-reuse tests.
- consus S3: SigV4 known-answer tests from AWS's published vectors; a
  byte-identical `GetObject(Range)`/`HeadObject` differential against
  `rusoto_s3`, run in-process and additionally against a pinned MinIO container
  in CI.
- The comparative benchmark baseline is recorded and passes at `0.9616`, but
  it does not authorize package-owned S3 integration. Consus packages contain
  no online-storage client in the next breaking release; any additional
  performance cells are historical audit evidence rather than a release gate.

<a id="atlas-pub-008"></a>
## ATLAS-PUB-008 — Audit facade names immediately before each first publish [chore] — todo

- Owner: unclaimed; scope: the pre-publish check only.
- Decision: [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md) §3,
  verification item 1.
- Outcome: name availability is a point-in-time observation and decays — 165 of
  173 names were free on 2026-07-28, and first-come means any of them can be
  claimed by a third party before the stack publishes. Each first publish
  re-checks its own name.
- Acceptance: `GET /api/v1/crates/<name>` returns 404 immediately before the
  publish, recorded in the release evidence. A collision discovered here is
  resolved by ADR 0037 §3's rule, not by an ad-hoc name.


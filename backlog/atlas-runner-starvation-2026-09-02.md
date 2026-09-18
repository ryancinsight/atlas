<a id="atlas-runner-starvation-2026-09-02"></a>
## ATLAS-RUNNER-STARVATION-2026-09-02 — Hosted runner queue starves every verification run [infra] — todo (Ask-User)

- **Re-measured 2026-09-09 17:48 UTC -- the queue is no longer slow, it is
  stopped.** Every one of the last nine kwavers runs is `queued` with zero jobs
  started; the oldest was created 16:44 and had waited **64 minutes** at the
  time of reading, the newest 17 minutes. The only non-queued run in the window
  is `cancelled`. `gh api repos/ryancinsight/kwavers/actions/runners` reports
  `total_count: 0`, so nothing self-hosted can absorb this, and every workflow
  targets `ubuntu-latest`. The 2026-09-02 numbers below measured a slow queue;
  this is a stationary one, which reads as a spending cap, a billing stop, or a
  platform outage rather than depth -- `gh` cannot tell which, because the
  billing endpoint needs a `user` token scope this session does not carry
  (refreshing auth scope is itself an Ask-User change).
- **Consequence for delivery, per the standing unavailability rule:** the venue
  is down, not the verification. Code work continues on the local pre-push gate
  (kwavers#754 landed it: fmt, clippy, and affected tests in 9s). The exception
  is a change *to* a workflow, whose only real gate is CI itself -- kwavers#755
  is held open rather than admin-merged for exactly that reason, since no local
  evidence can stand in for it.
- **Ask-User, second question alongside the runner registration below:** is
  there a spending cap or billing stop on the account? Nothing merges through
  hosted verification until it lifts.
- **Measured 2026-09-02 17:40 UTC, job-level queue wait (job `started_at` minus run `created_at`), 56 jobs across atlas and kwavers:**
  median 447 s, p90 2146 s, max 44.7 min. The longest waits are kwavers's own gates — Memory Safety (Miri) and Solver Validation Suite
  both 44.7 min, Heavy Validation 39.7, Code Quality 37.4. Stack-wide at that moment: 10 runs queued, 3 running.
- **What that costs:** the workflow-hygiene target is five minutes of *runtime* per verification job, and the median job waits longer than
  that before it starts. Today's seventeen SemVer-gate adoption pull requests took over an hour to clear the queue, and this session's
  merge waiters spent their time on queue rather than on checks. A job queued past its own runtime target is starvation by the standing
  rule, cured by capacity or by load-shedding, not by waiting.
- **The decision is still the user's** (registering a runner is an access change): a self-hosted runner on the local machine would take
  both the queue wait and the metered minutes to zero for private repositories, and the same registration with a `cuda` label would
  un-dark kwavers's GPU parity oracles, whose scheduled run is cancelled every night having never been assigned a runner.

- **Finding (2026-09-02):** with ~25 small PRs and the peers' pushes in flight, every job across the organization sat `queued` for tens of minutes to over an hour: kwavers#687 timed out a 60-minute merge gate with 27/29 checks green and two still queued; kwavers#691 shows 21 of 29 checks pending after an hour; atlas's own conformance runs queued for hours (`fb616d9f`, `7264f91e`). The queue-time rule (engineering_gates: workflow hygiene) makes a job queued past its runtime target an infrastructure defect, not agent waiting — and it is what turned today's shared-group cancellation into a class (`ATLAS-DEFAULT-BRANCH-CANCEL-2026-09-02`): pending runs superseding each other only bites when nothing ever starts.
- **Cure:** capacity or load-shedding. Load-shedding already applied today: path-filtered adoption workflows, staged waves. Load-shedding still owed by members: consus runs 81 checks per pull request (Check × 15 packages, Test × packages, MSRV × 15, fuzz builds) — a matrix that recompiles per cell instead of one archive sharded across runners (engineering_gates: build-once topology); a consus row. Capacity is the standing policy for private repositories and trusted-contributor stacks: a self-hosted runner on owned hardware with a persistent warm `CARGO_TARGET_DIR`/sccache, so no run pays cold setup or a metered minute. **Ask-User:** register one or more self-hosted runners at the organization level (labels `self-hosted, linux, x64`; the RTX 5080 host can also carry the `cuda` label the kwavers GPU-parity schedule already targets) — `gh` cannot register runners (hosting/security setting). Until then the waves stay staged and merge gates re-launch at their cap.
- **Acceptance oracle:** `gh run list --json createdAt,startedAt` across the stack shows median queue time under the five-minute job target; the kwavers `GPU Parity (scheduled)` row in `ATLAS-DEFAULT-BRANCH-REDS-2026-09-02` turns green.


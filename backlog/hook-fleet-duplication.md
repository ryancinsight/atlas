<a id="hook-fleet-duplication"></a>
## ATLAS-HOOK-FLEET-DUPLICATION-2026-09-06 - Twenty-two hand-maintained copies of two git hooks [patch] - in-progress

- **outcome:** `scripts/git-hooks/` is the one source for the member-side
  `pre-commit` and `pre-push` guards, deployed outward by
  `atlas-lock-form.py sync-hooks` under the generator contract, with
  `sync-hooks --check` failing CI on drift.
- **measured 2026-09-06:** 22 members carry `.githooks/pre-push` in **two**
  versions and `.githooks/pre-commit` in **two** versions. In both cases the
  minority version is `hephaestus`, and in both cases hephaestus is the one
  that is *correct*: it injects `safe.directory` so the hook's child git calls
  work in a checkout owned by a different filesystem account. Twenty-one
  members are missing that fix. The copies were the divergence, and the
  canonical copy in `scripts/git-hooks/` was staler than all of them — its
  `pre-commit` was 34 lines against the members' 61, missing the whole
  commit-time guard added under
  `ATLAS-LOCKFILE-POISONING-GENERATOR-2026-08-26`.
- **why the copies cannot simply be deleted:** `install-hooks` points
  `core.hooksPath` at the Atlas tree, which only resolves inside the stack
  checkout. A member cloned standalone would then run no hooks at all. So the
  copies stay and stop being *authored*: one source, written outward,
  drift-checked.
- **a behaviour fix rides with it.** `pre-push` ran `lockfile.py --check`
  against the *working tree* on every push, regardless of what the push
  contained. Those differ whenever the pushed commits were not checked out — a
  plumbing push, or a push from a tree sitting on another branch — and the hook
  then refused a push on the strength of state that push did not contain. It
  blocked four of the nine wheel-pin pushes today
  ([`#python-pipeline-pin-divergence`](backlog.md#python-pipeline-pin-divergence)),
  none of which touched a manifest or a lock. It now reads the revision range
  git supplies on stdin and skips when nothing in it is a `Cargo.toml` or
  `Cargo.lock`. Verified both directions: a workflow-only range skips, a range
  containing a lockfile change runs the real check, a branch deletion skips.
- **deployed 2026-09-08.** Twenty-three members synced and three more
  (`eunomia`, `iris`, `melinoe`) given hooks they had never had. Twenty landed
  immediately; `apollo`, `coeus`, `hephaestus` and the three new ones are
  enqueued behind required checks. Verified against each member's *default
  branch* rather than its working tree — 20 of 23 confirmed byte-identical to
  `scripts/git-hooks/` at the time of writing.
- **a verification trap worth recording.** `sync-hooks --check` reads working
  trees, and most member trees sit on peer branches, so it still reported 45
  drifted files after twenty deliveries had merged. The instrument was
  measuring checkouts, not delivered state — the same class of blind spot as
  the conformance ratchet measuring pinned gitlinks. Confirming delivery took
  comparing blob hashes at `origin/<default>` directly.
- **and a shell trap under it.** The first such comparison reported *zero*
  members in sync, because Git Bash rewrote `origin/main:.githooks/pre-push`
  into `origin\main;.githooks\pre-push` — MSYS path conversion mangling the
  revision:path argument. Every `rev-parse` failed and the loop counted the
  failures as mismatches. `MSYS_NO_PATHCONV=1` fixes it. A measurement that
  reports total failure deserves suspicion before its subject does.
- **`metis` and `prometheus`** are unregistered members without remotes and are
  out of scope until `#metis-unregistered-member` (`161354f`)
  clears.
- **acceptance:** `atlas-lock-form.py sync-hooks --check` exits zero across the
  fleet and runs in CI.


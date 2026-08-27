#!/usr/bin/env bash
# Deliver the lockfile pre-commit guard (apollo pilot 5602a20d) to the
# remaining fleet members. One branch/PR per member; the guard content is
# identical to the pilot. Handles per-member default branches and the
# overlay-flattened working-tree lock (SKIP_LOCKFILE_CHECK) that some members
# carry.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# harmonia is deliberately excluded: it has no scripts/lockfile.py and its
# committed lock is already flattened (0 first-party sources vs 4 declared git
# deps), so it needs regeneration plus the script added — a separate increment.
MEMBERS=(aequitas asclepius athena CFDrs coeus consus gaia helios horae
         hyperion mnemosyne moirai proteus ritk themis tyche)

for r in "${MEMBERS[@]}"; do
  echo "===== $r ====="
  # Default branch: main everywhere in this list except hephaestus (master,
  # already delivered) — keep it simple and resolve from the remote.
  git -C "repos/$r" fetch -q origin 2>/dev/null || true
  def=$(git -C "repos/$r" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||' || echo main)
  echo "  default branch: $def"

  # Fresh branch off the remote default, discarding any local state.
  git -C "repos/$r" checkout -q -B "fix/$r-lockfile-precommit-guard" "origin/$def"

  python scripts/apply-lockfile-guard.py "repos/$r"
  cp /tmp/pilot-pre-commit "repos/$r/.githooks/pre-commit"

  git -C "repos/$r" add scripts/lockfile.py .githooks/pre-commit
  git -C "repos/$r" commit -q -m "fix($r): Guard the lockfile at commit rather than only at push

The pre-push hook already refuses a flattened Cargo.lock and documents
why: cargo discovers the stack's [patch] overlay by walking up from the
working directory, so any build against a tree under the stack root
strips every git source from the lock. What it cannot do is prevent the
commit, and that turns out to be where the damage is.

By push time the lock is committed, often several commits back and mixed
with real work, so repairing it means editing history rather than
regenerating a file. In practice the branch is abandoned instead. This
adds the pre-commit hook from the apollo pilot (5602a20d) plus the
--check-staged surface in scripts/lockfile.py, so a poisoned lock never
enters a commit (ATLAS-LOCKFILE-POISONING-GENERATOR-2026-08-26)."

  # The working-tree Cargo.lock may be overlay-flattened (not part of this
  # commit); the committed lock is intact. Bypass only for the push.
  if ! git -C "repos/$r" push -q -u origin "fix/$r-lockfile-precommit-guard" 2>/tmp/pusherr.txt; then
    if grep -q "SKIP_LOCKFILE_CHECK\|no first-party git sources" /tmp/pusherr.txt; then
      SKIP_LOCKFILE_CHECK=1 git -C "repos/$r" push -q -u origin "fix/$r-lockfile-precommit-guard"
    else
      cat /tmp/pusherr.txt
      exit 1
    fi
  fi
  echo "  pushed"
done

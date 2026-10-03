# shellcheck shell=bash
#
# The canonical Atlas worktree, found from any linked lane of it.
#
# `.githooks/pre-commit` and `.githooks/pre-push` source this file, so one
# definition serves both. It defines functions and runs nothing.

# A linked Atlas worktree materializes a gitlink as an empty directory until
# someone initializes that member in the lane.  The canonical main worktree
# already owns the member checkout and its object store; use it for a
# read-only ref probe instead of treating the lane directory as the Atlas
# superproject.  The hook never initializes or changes the member checkout.
#
# canonical_stack_root <worktree>: prints the top level of the canonical
# worktree of the repository `worktree` belongs to, and returns 1 when it
# cannot name one.
canonical_stack_root() {
  local top="$1" common_dir common_norm configured ancestor candidate candidate_gitfile candidate_gitdir candidate_norm
  common_dir="$(git -C "$top" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 1
  common_norm="$(printf '%s' "$common_dir" | tr '\\' '/' | tr '[:upper:]' '[:lower:]')"
  if [ "$(basename "$common_dir")" = ".git" ]; then
    dirname "$common_dir"
    return 0
  fi
  configured="$(git --git-dir="$common_dir" config --path core.worktree 2>/dev/null || true)"
  if [ -n "$configured" ]; then
    git -C "$configured" rev-parse --show-toplevel
    return 0
  fi
  scan_candidate() {
    local root="$1" depth="$2" candidate_gitfile candidate candidate_gitdir candidate_norm child
    [ "$depth" -le 6 ] || return 1
    for candidate_gitfile in "$root"/*/.git; do
      [ -f "$candidate_gitfile" ] || continue
      candidate_gitfile="${candidate_gitfile//\\//}"
      candidate="${candidate_gitfile%/.git}"
      candidate_gitdir="$(sed -n 's/^gitdir: //p' "$candidate/.git" 2>/dev/null || true)"
      case "$candidate_gitdir" in
        /*|[A-Za-z]:/*) ;;
        *) candidate_gitdir="$candidate/$candidate_gitdir" ;;
      esac
      candidate_norm="$(printf '%s' "$candidate_gitdir" | tr '\\' '/' | tr '[:upper:]' '[:lower:]')"
      if [ "$candidate_norm" = "$common_norm" ]; then
        git -C "$candidate" rev-parse --show-toplevel
        return 0
      fi
    done
    for child in "$root"/*; do
      [ -d "$child" ] || continue
      scan_candidate "$child" "$((depth + 1))" && return 0
    done
    return 1
  }
  # `git init --separate-git-dir` leaves the main worktree's `.git` file as
  # the only canonical-worktree marker; unlike a linked lane, it points at
  # the common directory itself. Search only ancestor siblings of Git's
  # metadata and validate each candidate through Git, so lane ordering and
  # metadata-parent assumptions cannot select a worktree by position.
  ancestor="$(dirname "$top")"
  while [ -n "$ancestor" ] && [ "$ancestor" != "/" ]; do
    scan_candidate "$ancestor" 0 && return 0
    [ "$ancestor" = "$(dirname "$ancestor")" ] && break
    ancestor="$(dirname "$ancestor")"
  done
  ancestor="$(dirname "$(dirname "$common_dir")")"
  while [ -n "$ancestor" ] && [ "$ancestor" != "/" ]; do
    scan_candidate "$ancestor" 0 && return 0
    [ "$ancestor" = "$(dirname "$ancestor")" ] && break
    ancestor="$(dirname "$ancestor")"
  done
  return 1
}

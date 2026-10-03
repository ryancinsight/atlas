# shellcheck shell=bash
#
# The canonical Atlas worktree, found from any linked lane of it.
#
# `.githooks/pre-commit` and `.githooks/pre-push` source this file, so one
# definition serves both. It defines functions and runs nothing. It needs
# bash 4 or later (`${var,,}`): Git for Windows and Linux CI ship bash 5.

# Windows spells one path several ways and folds its case; POSIX does neither.
case "${OSTYPE-}" in
  msys*|cygwin*) _stack_root_windows=1 ;;
  *) _stack_root_windows=0 ;;
esac

# Sets REPLY to the key by which two spellings of one path compare equal.
_stack_root_key() {
  REPLY="$1"
  if [ "$_stack_root_windows" = 1 ]; then
    REPLY="${REPLY//\\//}"
    REPLY="${REPLY,,}"
  fi
}

# Sets REPLY to the key of directory `$1` as the filesystem spells it: links
# resolved and, on Windows, short 8.3 names expanded, which is how Git compares
# a ceiling with the directory it would enter. A path that is not a directory
# keys as written.
_stack_root_physical_key() {
  local previous="$PWD"
  if CDPATH= cd -P -- "$1" >/dev/null 2>&1; then
    _stack_root_key "$PWD"
    cd -- "$previous"
  else
    _stack_root_key "$1"
  fi
}

# Sets `_stack_root_ceilings` to the keys of the directories named in
# GIT_CEILING_DIRECTORIES, the list Git's own discovery refuses to enter. The
# entries are `;`-separated, or `:`-separated unless the list opens with a drive
# letter on Windows, where the colon of `C:/dir` is no separator.
_stack_root_load_ceilings() {
  local list="${GIT_CEILING_DIRECTORIES-}" entry
  local -a entries=()
  _stack_root_ceilings=()
  [ -n "$list" ] || return 0
  case "$list" in
    *\;*) IFS=';' read -r -a entries <<<"$list" ;;
    [A-Za-z]:[/\\]*)
      if [ "$_stack_root_windows" = 1 ]; then
        entries=("$list")
      else
        IFS=':' read -r -a entries <<<"$list"
      fi
      ;;
    *) IFS=':' read -r -a entries <<<"$list" ;;
  esac
  for entry in "${entries[@]}"; do
    [ -n "$entry" ] || continue
    _stack_root_physical_key "$entry"
    _stack_root_ceilings+=("$REPLY")
  done
}

# Succeeds when directory `$1` is a ceiling.
_stack_root_at_ceiling() {
  local ceiling
  [ "${#_stack_root_ceilings[@]}" -gt 0 ] || return 1
  _stack_root_physical_key "$1"
  for ceiling in "${_stack_root_ceilings[@]}"; do
    [ "$ceiling" = "$REPLY" ] && return 0
  done
  return 1
}

# Prints the top level of the worktree below `$1`, at most six directories
# deep, whose `.git` file names the common directory with key `$3`.
_stack_root_scan() {
  local root="$1" depth="$2" common_key="$3" candidate_gitfile candidate candidate_gitdir child line
  [ "$depth" -le 6 ] || return 1
  for candidate_gitfile in "$root"/*/.git; do
    [ -f "$candidate_gitfile" ] || continue
    candidate_gitfile="${candidate_gitfile//\\//}"
    candidate="${candidate_gitfile%/.git}"
    candidate_gitdir=""
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line%$'\r'}"
      case "$line" in "gitdir: "*) candidate_gitdir="${line#gitdir: }" ;; esac
    done < "$candidate/.git" 2>/dev/null
    case "$candidate_gitdir" in
      /*|[A-Za-z]:/*) ;;
      *) candidate_gitdir="$candidate/$candidate_gitdir" ;;
    esac
    _stack_root_key "$candidate_gitdir"
    if [ "$REPLY" = "$common_key" ]; then
      git -C "$candidate" rev-parse --show-toplevel
      return 0
    fi
  done
  for child in "$root"/*; do
    [ -d "$child" ] || continue
    _stack_root_scan "$child" "$((depth + 1))" "$common_key" && return 0
  done
  return 1
}

# Searches directory `$1` and then each of its ancestors, nearest first, for the
# worktree owning the common directory with key `$2`. The search ends at the
# filesystem root or at a ceiling, without entering the ceiling, as Git's own
# discovery does.
_stack_root_search() {
  local ancestor="$1" common_key="$2"
  while [ -n "$ancestor" ] && [ "$ancestor" != "/" ]; do
    _stack_root_at_ceiling "$ancestor" && return 1
    _stack_root_scan "$ancestor" 0 "$common_key" && return 0
    [ "$ancestor" = "${ancestor%/*}" ] && return 1
    ancestor="${ancestor%/*}"
  done
  return 1
}

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
  local top="$1" common_dir common_key configured ancestor
  common_dir="$(git -C "$top" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 1
  if [ "${common_dir##*/}" = ".git" ]; then
    printf '%s\n' "${common_dir%/*}"
    return 0
  fi
  _stack_root_key "$common_dir"
  common_key="$REPLY"
  configured="$(git --git-dir="$common_dir" config --path core.worktree 2>/dev/null || true)"
  if [ -n "$configured" ]; then
    git -C "$configured" rev-parse --show-toplevel
    return 0
  fi
  _stack_root_load_ceilings
  # `git init --separate-git-dir` leaves the main worktree's `.git` file as
  # the only canonical-worktree marker; unlike a linked lane, it points at
  # the common directory itself. Search only ancestor siblings of Git's
  # metadata and validate each candidate through Git, so lane ordering and
  # metadata-parent assumptions cannot select a worktree by position.
  _stack_root_search "${top%/*}" "$common_key" && return 0
  ancestor="${common_dir%/*}"
  _stack_root_search "${ancestor%/*}" "$common_key"
}

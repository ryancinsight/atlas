"""Local actions reached through the `path:` of an `actions/checkout` step.

A job that runs `actions/checkout` with `path: P` and later calls
`uses: ./P/<rest>` finds the action at `<rest>` in that checkout. The lint
guard resolves `./P/<rest>` as `./<rest>` in the candidate only when the
checkout can be shown to hold the candidate's tree:

* the step defines a prefix when it uses `actions/checkout@<anything>` and its
  `with.path` is a plain relative path: a string scalar with no `${{`, no
  backslash, and no empty, `.` or `..` component (a leading `/` leaves an
  empty component);
* the prefix qualifies when the step has no `with.repository` and its
  `with.ref` is absent or, ignoring whitespace inside `${{ }}`, one of
  `CANDIDATE_REFS`;
* the latest checkout step before a reference whose path contains the
  reference governs it, within the same job: a later checkout may clean or
  replace what an earlier one placed, so an overlapping later path wins even
  when it does not qualify.

On a pull request the candidate is the merge commit, while a head-SHA checkout
supplies the action as the head defines it. The guard analyses the copy in the
candidate; that is the one approximation.

References inside a composite action reached through a prefix, and
reusable-workflow (`jobs.<id>.uses`) references, resolve against the candidate
root only.
"""

import re
from collections.abc import Callable
from typing import NamedTuple

from yaml.nodes import Node, ScalarNode
from yaml.resolver import BaseResolver

CANDIDATE_REFS = (
    "${{ github.sha }}",
    "${{ github.event.pull_request.head.sha }}",
    "${{ github.event.pull_request.head.sha || github.sha }}",
)
_EXPRESSION = re.compile(r"\$\{\{(.*)\}\}")


class Checkout(NamedTuple):
    """A checkout path and whether the checkout holds the candidate's tree."""

    prefix: str
    holds_candidate: bool


Checkouts = dict[str, Checkout]


def _text(node: Node | None) -> str | None:
    if isinstance(node, ScalarNode) and node.tag == BaseResolver.DEFAULT_SCALAR_TAG:
        return node.value
    return None


def _expression(value: str) -> str | None:
    match = _EXPRESSION.fullmatch(value.strip())
    return None if match is None else "".join(match.group(1).split())


_CANDIDATE_EXPRESSIONS = frozenset(_expression(spelling) for spelling in CANDIDATE_REFS)


def _plain_path(node: Node | None) -> str | None:
    path = _text(node)
    if path is None or "${{" in path or "\\" in path:
        return None
    return None if any(part in ("", ".", "..") for part in path.split("/")) else path


def checkout(uses: str, step: Node, field: Callable[[Node | None, str], Node | None]) -> Checkout | None:
    """The prefix a step defines, or `None` when it is not a path checkout; `field` reads mapping fields."""
    options = field(step, "with")
    prefix = _plain_path(field(options, "path")) if uses.startswith("actions/checkout@") else None
    if prefix is None:
        return None
    ref = field(options, "ref")
    names_candidate = ref is None or _expression(_text(ref) or "") in _CANDIDATE_EXPRESSIONS
    return Checkout(prefix, field(options, "repository") is None and names_candidate)


def resolve(reference: str, checkouts: Checkouts) -> tuple[str, Checkout | None]:
    """Split `./P/<rest>` into `./<rest>` and its governing checkout, the latest defined, if any."""
    governing = [found for found in checkouts.values() if reference.startswith(f"./{found.prefix}/")]
    if not governing:
        return reference, None
    latest = governing[-1]
    return f"./{reference[len(latest.prefix) + 3 :]}", latest


def preceding(steps: list[tuple[ScalarNode, Checkout | None]]) -> list[tuple[ScalarNode, Checkouts]]:
    """Pair each step's `uses` with the checkouts defined by the steps before it."""
    found: list[tuple[ScalarNode, Checkouts]] = []
    checkouts: Checkouts = {}
    for uses, defined in steps:
        found.append((uses, dict(checkouts)))
        if defined is not None:
            checkouts.pop(defined.prefix, None)
            checkouts[defined.prefix] = defined
    return found

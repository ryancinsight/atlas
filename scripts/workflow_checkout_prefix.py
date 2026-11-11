"""Local actions reached through the `path:` of an `actions/checkout` step.

A job that runs `actions/checkout` with `path: P` and later calls `uses: ./P/<rest>` finds the action at
`<rest>` in that checkout. The lint guard resolves `./P/<rest>` as `./<rest>` in the candidate only while that
checkout is shown to hold the candidate's tree. Within one job, in step order:

* every step whose `uses` names `actions/checkout@<anything>`, in any letter case, is read. Its location is
  known when `with.path` is a plain relative path: a string scalar with no `${{`, no backslash, and no empty,
  `.` or `..` component. A step with no path (the workspace root), any other path, or a `with` block that
  cannot be read input by input (not one mapping, a merge key, a non-string name, or a name repeated in any
  letter case) has an unknown location;
* a checkout of unknown location voids every prefix defined before it. A checkout of a known path voids each
  earlier prefix that is its ancestor, its descendant or equal to it, comparing components without letter
  case, and then defines its own path as a prefix. The prefixes in force are therefore pairwise unrelated, and
  no later checkout has written into any of them;
* a prefix holds the candidate when its step passes no input outside `CANDIDATE_INPUTS`, spelled exactly, and
  its `ref` is absent or one of `CANDIDATE_REFS`, ignoring whitespace around the operands inside `${{ }}`;
* a reference whose path lies under a prefix in force, or equals it, is governed by that prefix. Every other
  reference resolves against the candidate root exactly as written.

Assumed and not checked: `actions/checkout` writes the tracked files of the commit it names into its path, and
no step of another kind changes them. On a pull request the candidate is the merge commit, while a head-SHA
checkout supplies the action as the head defines it; the guard analyses the copy in the candidate.

References inside a composite action reached through a prefix, and reusable-workflow (`jobs.<id>.uses`)
references, resolve against the candidate root only.
"""

import re
from typing import NamedTuple

from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.resolver import BaseResolver

CANDIDATE_INPUTS = frozenset(("path", "ref", "fetch-depth", "fetch-tags", "persist-credentials", "clean", "lfs"))
CANDIDATE_REFS = (
    "${{ github.sha }}",
    "${{ github.event.pull_request.head.sha }}",
    "${{ github.event.pull_request.head.sha || github.sha }}",
)
_EXPRESSION = re.compile(r"\$\{\{(.*)\}\}")


class Checkout(NamedTuple):
    """A checkout path in force and whether its checkout holds the candidate's tree."""

    prefix: str
    holds_candidate: bool


def _text(node: Node | None) -> str | None:
    plain = isinstance(node, ScalarNode) and node.tag == BaseResolver.DEFAULT_SCALAR_TAG
    return node.value if plain else None


def _operands(value: str | None) -> tuple[str, ...] | None:
    match = None if value is None else _EXPRESSION.fullmatch(value)
    return None if match is None else tuple(operand.strip() for operand in match.group(1).split("||"))


_CANDIDATE_OPERANDS = frozenset(_operands(spelling) for spelling in CANDIDATE_REFS)


def _values(node: Node | None, name: str) -> list[Node]:
    if not isinstance(node, MappingNode):
        return []
    return [value for key, value in node.value if isinstance(key, ScalarNode) and key.value == name]


def _inputs(step: Node) -> dict[str, Node] | None:
    """A checkout step's inputs by name as written, or `None` when they cannot be read input by input."""
    blocks = _values(step, "with")
    if not blocks:
        return {}
    if len(blocks) != 1 or not isinstance(blocks[0], MappingNode):
        return None
    names = [_text(key) for key, _ in blocks[0].value]
    if None in names or len({name.casefold() for name in names}) != len(names):
        return None
    return {name: value for name, (_, value) in zip(names, blocks[0].value)}


def _checkout(step: Node) -> Checkout | None:
    """The prefix a checkout step defines, or `None` when its location is unknown."""
    inputs = _inputs(step)
    path = None if inputs is None else _text(inputs.get("path"))
    if path is None or "${{" in path or "\\" in path or any(part in ("", ".", "..") for part in path.split("/")):
        return None
    ref = inputs.get("ref")
    named = ref is None or _operands(_text(ref)) in _CANDIDATE_OPERANDS
    return Checkout(path, named and set(inputs) <= CANDIDATE_INPUTS)


def _related(first: str, second: str) -> bool:
    one, other = first.casefold().split("/"), second.casefold().split("/")
    shared = min(len(one), len(other))
    return one[:shared] == other[:shared]


def governing(document: Node) -> dict[int, Checkout | None]:
    """Map the identity of each local `uses` node of a workflow's steps to the prefix that governs it."""
    found: dict[int, Checkout | None] = {}
    jobs = [job for block in _values(document, "jobs") if isinstance(block, MappingNode) for _, job in block.value]
    for steps in (steps for job in jobs for steps in _values(job, "steps") if isinstance(steps, SequenceNode)):
        in_force: list[Checkout] = []
        for step in steps.value:
            nodes = _values(step, "uses")
            reference = _text(nodes[0]) if len(nodes) == 1 else None
            if reference is None:
                continue
            if reference.casefold().startswith("actions/checkout@"):
                defined = _checkout(step)
                unrelated = [held for held in in_force if defined and not _related(held.prefix, defined.prefix)]
                in_force = unrelated + [defined] if defined else []
            elif reference.startswith("./"):
                over = next((held for held in in_force if f"{reference}/".startswith(f"./{held.prefix}/")), None)
                known = found.setdefault(id(nodes[0]), over)
                if known != over:
                    # One aliased node read under two different prefixes has no single meaning.
                    found[id(nodes[0])] = Checkout((known or over).prefix, False)
    return found

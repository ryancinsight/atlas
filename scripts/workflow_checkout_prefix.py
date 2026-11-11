"""Local actions reached through the `path:` of an `actions/checkout` step.

A job that runs `actions/checkout` with `path: P` and later calls `uses: ./P/<rest>` finds the action at
`<rest>` in that checkout. The lint guard resolves `./P/<rest>` as `./<rest>` in the candidate only when each
link below is on an allow-list. Within one job, in step order:

* a step that is not a mapping of distinct lower-case string keys without padding, or whose `uses` is neither
  a `./` reference nor `owner/repository[/path]@ref` in plain characters (`_REMOTE`), may be a checkout of any
  location: it voids every prefix defined before it;
* a step whose `uses` names the repository `actions/checkout`, without letter case, is a checkout. Its location
  is known when `with` is one mapping of distinct string names and `path` matches `_PLAIN_PATH`; otherwise it
  voids every prefix. A known path voids each earlier prefix that is its ancestor, its descendant or equal to
  it, without letter case, and then defines its own path as a prefix;
* a prefix holds the candidate when its step has no key outside `STEP_KEYS` (so it always runs), names
  `actions/checkout@<ref>` with no path inside the repository, passes no input outside `CANDIDATE_INPUTS` and
  has no `ref` or one of `CANDIDATE_REFS`, ignoring spaces and tabs around the operands inside `${{ }}`;
* a reference at or under a prefix in force, compared without letter case, is governed by it, and a reference
  that is not a plain path (`_PLAIN_PATH`, no `.git` component) is governed by a prefix in force even when it
  names none. A governed reference is shown to load the candidate only when the prefix holds the candidate,
  the reference is a plain path that spells the prefix exactly, and the calling step has no key outside
  `STEP_KEYS`. Every other reference maps to `None` and resolves against the candidate root as written.

Assumed and not checked: `actions/checkout` writes the tracked files of the commit it names into its path and
nothing else that a reference can name; no step of another kind (`run`, another action, a local composite
action) changes them; and the workflow runs on an event where `github.sha` or the pull-request head is the
commit analysed (`workflow_call` and `pull_request_target` are not). References inside composite actions and
reusable-workflow references are not read. The rule reads no tree, so it cannot see a symbolic link inside a
checkout; `atlas_workflow_lint` rejects a reference through a link when it resolves the reference.
"""

import re
from typing import NamedTuple

from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.resolver import BaseResolver

STEP_KEYS = frozenset(("name", "id", "uses", "with"))
CANDIDATE_INPUTS = frozenset(("path", "ref", "fetch-depth", "persist-credentials"))
CANDIDATE_REFS = (
    "${{ github.sha }}",
    "${{ github.event.pull_request.head.sha }}",
    "${{ github.event.pull_request.head.sha || github.sha }}",
)
METADATA_NAMES = ("action.yml", "action.yaml")
_EXPRESSION = re.compile(r"\$\{\{(.*)\}\}")
_COMPONENT = r"\.?[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*"
_PLAIN_PATH = re.compile(rf"{_COMPONENT}(?:/{_COMPONENT})*")
_REMOTE = re.compile(r"([\w.-]+/[\w.-]+)(/[\w./-]+)?@[\w./-]+", re.ASCII)


class Checkout(NamedTuple):
    """A checkout path in force and whether a reference under it is shown to load the candidate's tree."""

    prefix: str
    holds_candidate: bool


def _text(node: Node | None) -> str | None:
    plain = isinstance(node, ScalarNode) and node.tag == BaseResolver.DEFAULT_SCALAR_TAG
    return node.value if plain else None


def _operands(value: str | None) -> tuple[str, ...] | None:
    match = None if value is None else _EXPRESSION.fullmatch(value)
    return None if match is None else tuple(operand.strip(" \t") for operand in match.group(1).split("||"))


_CANDIDATE_OPERANDS = frozenset(_operands(spelling) for spelling in CANDIDATE_REFS)


def _values(node: Node | None, name: str) -> list[Node]:
    if not isinstance(node, MappingNode):
        return []
    return [value for key, value in node.value if isinstance(key, ScalarNode) and key.value == name]


def _entries(node: Node | None) -> dict[str, Node] | None:
    """A mapping's values by key as written, or `None` when it cannot be read key by key."""
    if not isinstance(node, MappingNode):
        return None
    names = [_text(key) for key, _ in node.value]
    if None in names or len({name.strip().casefold() for name in names}) != len(names):
        return None
    return {name: value for name, (_, value) in zip(names, node.value)}


def _checkout(step: dict[str, Node], named: bool) -> Checkout | None:
    """The prefix a checkout step defines, or `None` when its location is unknown."""
    inputs = _entries(step["with"]) if "with" in step else {}
    path = None if inputs is None else _text(inputs.get("path"))
    if path is None or not _PLAIN_PATH.fullmatch(path):
        return None
    ref = inputs.get("ref")
    candidate = ref is None or _operands(_text(ref)) in _CANDIDATE_OPERANDS
    return Checkout(path, named and candidate and set(step) <= STEP_KEYS and set(inputs) <= CANDIDATE_INPUTS)


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
        for node in steps.value:
            step = _entries(node)
            if step is not None and any(name != name.strip().casefold() for name in step):
                step = None
            nodes = _values(node, "uses")
            reference = _text(nodes[0]) if len(nodes) == 1 else None
            if reference is not None and reference.startswith("./"):
                under, parts = f"{reference}/".casefold(), reference[2:].casefold().split("/")
                plain = _PLAIN_PATH.fullmatch(reference[2:]) is not None and ".git" not in parts
                over = next((held for held in in_force if under.startswith(f"./{held.prefix}/".casefold())), None)
                if over is None and in_force and not plain:
                    over = in_force[0]
                exact = over is not None and plain and f"{reference}/".startswith(f"./{over.prefix}/")
                if over is not None and not (exact and step is not None and set(step) <= STEP_KEYS):
                    over = over._replace(holds_candidate=False)
                known = found.setdefault(id(nodes[0]), over)
                if known != over:
                    # One aliased node read under two different prefixes has no single meaning.
                    found[id(nodes[0])] = Checkout((known or over).prefix, False)
            uses = None if step is None else _text(step.get("uses"))
            remote = None if uses is None else _REMOTE.fullmatch(uses)
            if step is None or ("uses" in step and remote is None and not (uses or "").startswith("./")):
                in_force = []
            elif remote is not None and remote[1].casefold() == "actions/checkout":
                defined = _checkout(step, remote[2] is None)
                unrelated = [held for held in in_force if defined and not _related(held.prefix, defined.prefix)]
                in_force = unrelated + [defined] if defined else []
    return found


def place_copies(inputs: dict[str, bytes], copies: set[tuple[str, str]]) -> str | None:
    """Add each governed action's metadata under its checkout path, or name a directory with two sources."""
    sources: dict[str, str] = {}
    for prefix, metadata in sorted(copies):
        source = metadata.rpartition("/")[0]
        directory = f"{prefix}/{source}"
        owned = any(f"{directory}/{name}" in inputs for name in METADATA_NAMES)
        if owned or sources.setdefault(directory, source) != source:
            return directory
    inputs.update({f"{prefix}/{metadata}": inputs[metadata] for prefix, metadata in copies})
    return None

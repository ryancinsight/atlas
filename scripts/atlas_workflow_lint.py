"""Project validated same-repository references without changing other YAML bytes."""

import os
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

STRING_TAG = "tag:yaml.org,2002:str"


class WorkflowSourceError(ValueError):
    """A workflow source is ambiguous, mutable, or outside its candidate."""


def _children(node: Node) -> list[Node]:
    if isinstance(node, MappingNode):
        return [child for pair in node.value for child in pair]
    if isinstance(node, SequenceNode):
        return list(node.value)
    return []


def _ambiguous(root: Node) -> set[int]:
    counts = {id(root): 1}
    nodes: dict[int, Node] = {}
    pending = [root]
    while pending:
        node = pending.pop()
        if id(node) in nodes:
            continue
        nodes[id(node)] = node
        for child in _children(node):
            counts[id(child)] = counts.get(id(child), 0) + 1
            pending.append(child)
    found: set[int] = set()
    pending = [nodes[key] for key, count in counts.items() if count > 1]
    while pending:
        node = pending.pop()
        if id(node) not in found:
            found.add(id(node))
            pending.extend(_children(node))
    return found


def _field(node: Node | None, name: str) -> Node | None:
    if not isinstance(node, MappingNode):
        return None
    values = [value for key, value in node.value if isinstance(key, ScalarNode) and key.value == name]
    if len(values) > 1:
        raise WorkflowSourceError(f"duplicate {name!r} field")
    return values[0] if values else None


def _scalar(node: Node | None, name: str) -> ScalarNode | None:
    if node is not None and (not isinstance(node, ScalarNode) or node.tag != STRING_TAG):
        raise WorkflowSourceError(f"{name!r} must be a string scalar")
    return node


def _step_uses(steps: Node | None) -> list[ScalarNode]:
    if steps is None:
        return []
    if not isinstance(steps, SequenceNode):
        raise WorkflowSourceError("'steps' must be a sequence")
    return [uses for step in steps.value if (uses := _scalar(_field(step, "uses"), "uses"))]


def _references(document: Node, kind: str) -> list[tuple[ScalarNode, str]]:
    if kind == "action":
        runs = _field(document, "runs")
        using = _scalar(_field(runs, "using"), "using")
        if using is None or using.value != "composite":
            return []
        return [(uses, "action") for uses in _step_uses(_field(runs, "steps"))]
    jobs = _field(document, "jobs")
    if not isinstance(jobs, MappingNode):
        raise WorkflowSourceError("workflow 'jobs' must be a mapping")
    found: list[tuple[ScalarNode, str]] = []
    for _, job in jobs.value:
        reusable = _scalar(_field(job, "uses"), "uses")
        if reusable is not None:
            found.append((reusable, "workflow"))
        found.extend((uses, "action") for uses in _step_uses(_field(job, "steps")))
    return found


def _resolved(root: Path, path: Path, reference: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as error:
        raise WorkflowSourceError(f"reference escapes or is missing from the checkout: {reference!r}") from error
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        if current.is_symlink():
            raise WorkflowSourceError(f"reference uses a symlink: {reference!r}")
    return resolved


def _target(root: Path, reference: str, kind: str) -> Path:
    if "@" in reference or "\\" in reference or not reference.startswith("$/"):
        raise WorkflowSourceError(f"invalid same-repository reference: {reference!r}")
    raw_parts = reference[2:].split("/")
    if not raw_parts or any(part in ("", ".", "..") for part in raw_parts):
        raise WorkflowSourceError(f"invalid same-repository path: {reference!r}")
    target = _resolved(root, root.joinpath(*raw_parts), reference)
    if kind == "workflow":
        workflows = root / ".github" / "workflows"
        if target.parent != workflows or target.suffix not in (".yml", ".yaml"):
            raise WorkflowSourceError(f"unsupported reusable workflow target: {reference!r}")
        return target
    metadata = [target / name for name in ("action.yml", "action.yaml") if os.path.lexists(target / name)]
    if len(metadata) != 1:
        raise WorkflowSourceError(f"action target needs exactly one metadata file: {reference!r}")
    return _resolved(root, metadata[0], reference)


def _sigil_offset(text: str, node: ScalarNode, path: Path) -> int:
    span = text[node.start_mark.index : node.end_mark.index]
    if node.style is None:
        relative = 0
    elif node.style in ("'", '"'):
        relative = 1
    else:
        header = span.find("\n")
        relative = header + 1
        while 0 < relative < len(span) and span[relative] in " \r\n":
            relative += 1
    if relative < 0 or not span.startswith("$/", relative):
        raise WorkflowSourceError(f"unsupported leading self-reference spelling in {path}")
    character = node.start_mark.index + relative
    return len(text[:character].encode("utf-8"))


def project(source: bytes, path: Path, root: Path, kind: str) -> tuple[bytes, list[Path]]:
    """Replace only validated leading `$` bytes in one YAML document."""
    try:
        text = source.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise WorkflowSourceError(f"workflow is not UTF-8: {path}") from error
    document = yaml.compose(text, Loader=yaml.SafeLoader)
    if document is None:
        raise WorkflowSourceError(f"empty YAML document: {path}")
    ambiguous = _ambiguous(document)
    offsets: list[int] = []
    targets: list[Path] = []
    for node, target_kind in _references(document, kind):
        if not node.value.startswith("$/"):
            continue
        if id(node) in ambiguous:
            raise WorkflowSourceError(f"aliased same-repository reference in {path}")
        offsets.append(_sigil_offset(text, node, path))
        targets.append(_target(root, node.value, target_kind))
    projected = bytearray(source)
    for offset in offsets:
        projected[offset] = ord(".")
    return bytes(projected), targets

"""Project same-repository references; candidate bytes must exactly match stored Git blobs."""

import os
import re
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

import process_tree


CONFIG_NAMES = ("actionlint.yaml", "actionlint.yml")
FULL_SHA = re.compile(r"[0-9a-f]{40}\Z")


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
    if node is not None and not isinstance(node, ScalarNode):
        raise WorkflowSourceError(f"{name!r} must be a scalar")
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
        span = text[node.start_mark.index : node.end_mark.index]
        relative = span.find("$/")
        if relative < 0 or span.find("$/", relative + 1) >= 0:
            raise WorkflowSourceError(f"ambiguous scalar spelling for {node.value!r}")
        character = node.start_mark.index + relative
        offsets.append(len(text[:character].encode("utf-8")))
        targets.append(_target(root, node.value, target_kind))
    projected = bytearray(source)
    for offset in offsets:
        projected[offset] = ord(".")
    return bytes(projected), targets


def _git(root: Path, *arguments: str, input: bytes | None = None) -> bytes:
    result = process_tree.run(["git", *arguments], cwd=root, input=input, timeout=30)
    if result.returncode != 0:
        raise WorkflowSourceError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def _checkout(root: Path, candidate: str) -> None:
    if not FULL_SHA.fullmatch(candidate):
        raise WorkflowSourceError("candidate must be a full lowercase commit SHA")
    checkout = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if checkout != root or _git(root, "rev-parse", "HEAD").decode().strip() != candidate:
        raise WorkflowSourceError("checkout does not match the declared candidate")
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise WorkflowSourceError("candidate checkout is not clean")


def _candidate_bytes(root: Path, candidate: str, path: Path) -> bytes:
    relative = path.relative_to(root).as_posix()
    expected = _git(root, "cat-file", "blob", f"{candidate}:{relative}")
    source = _resolved(root, path, relative).read_bytes()
    if source != expected:
        raise WorkflowSourceError(f"lint input differs from candidate {candidate}: {relative}")
    return source


def _inventory(root: Path, candidate: str) -> tuple[str, ...]:
    paths = _git(
        root, "ls-tree", "-r", "-z", "--name-only", candidate, "--",
        ".github/workflows",
        *(f".github/{name}" for name in CONFIG_NAMES),
    ).split(b"\0")
    return tuple(sorted(value.decode("utf-8", "strict") for value in paths if value))


def _working_inventory(root: Path) -> tuple[str, ...]:
    paths = [path for path in (root / ".github" / "workflows").glob("*") if path.suffix in (".yml", ".yaml")]
    paths.extend(root / ".github" / name for name in CONFIG_NAMES if os.path.lexists(root / ".github" / name))
    return tuple(sorted(path.relative_to(root).as_posix() for path in paths))


def _collect(root: Path, candidate: str, inventory: tuple[str, ...]) -> tuple[dict[Path, bytes], dict[Path, bytes]]:
    paths = [root / relative for relative in inventory]
    workflows = [path for path in paths if path.parent == root / ".github" / "workflows"]
    configs = [path for path in paths if path.name in CONFIG_NAMES]
    pending = [(path, "workflow") for path in workflows]
    queued = set(workflows)
    inputs = {path: _candidate_bytes(root, candidate, path) for path in configs}
    projected: dict[Path, bytes] = {}
    while pending:
        path, kind = pending.pop(0)
        source = _candidate_bytes(root, candidate, path)
        inputs[path] = source
        content, targets = project(source, path, root, kind)
        if kind == "workflow":
            projected[path] = content
        for target in targets:
            inputs[target] = _candidate_bytes(root, candidate, target)
            if target.parent != root / ".github" / "workflows" and target not in queued:
                queued.add(target)
                pending.append((target, "action"))
    return projected, inputs


def snapshot(root: Path, candidate: str) -> tuple[dict[Path, bytes], dict[Path, bytes]]:
    """Collect projected workflows and their candidate-owned lint inputs."""
    root = root.resolve()
    _checkout(root, candidate)
    inventory = _inventory(root, candidate)
    if _working_inventory(root) != inventory:
        raise WorkflowSourceError("workflow or actionlint config inventory differs from candidate")
    first = _collect(root, candidate, inventory)
    _checkout(root, candidate)
    if _inventory(root, candidate) != inventory or _working_inventory(root) != inventory:
        raise WorkflowSourceError("candidate lint inventory changed while projecting")
    if _collect(root, candidate, inventory) != first:
        raise WorkflowSourceError("candidate lint bytes changed while projecting")
    _checkout(root, candidate)
    return first

"""Validate and lint workflows using same-repository references."""

import argparse
import shutil
import sys
from pathlib import Path, PurePosixPath

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

import process_tree


class WorkflowLintError(Exception):
    pass


def _children(node: Node) -> list[Node]:
    if isinstance(node, MappingNode):
        return [child for pair in node.value for child in pair]
    if isinstance(node, SequenceNode):
        return list(node.value)
    return []


def _ambiguous_nodes(root: Node) -> set[int]:
    counts: dict[int, int] = {id(root): 1}
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
    ambiguous: set[int] = set()
    pending = [nodes[node_id] for node_id, count in counts.items() if count > 1]
    while pending:
        node = pending.pop()
        if id(node) in ambiguous:
            continue
        ambiguous.add(id(node))
        pending.extend(_children(node))
    return ambiguous


def _fields(node: Node, name: str) -> list[Node]:
    if not isinstance(node, MappingNode):
        return []
    return [value for key, value in node.value if isinstance(key, ScalarNode) and key.value == name]


def _one(node: Node, name: str) -> Node | None:
    fields = _fields(node, name)
    if len(fields) > 1:
        raise WorkflowLintError(f"duplicate {name!r} field")
    return fields[0] if fields else None


def _scalar(node: Node | None, field: str) -> ScalarNode | None:
    if node is None:
        return None
    if not isinstance(node, ScalarNode):
        raise WorkflowLintError(f"{field!r} must be a scalar")
    return node


def _step_references(steps: Node | None) -> list[ScalarNode]:
    if steps is None:
        return []
    if not isinstance(steps, SequenceNode):
        raise WorkflowLintError("'steps' must be a sequence")
    return [reference for step in steps.value if (reference := _scalar(_one(step, "uses"), "uses"))]


def _workflow_references(root: Node) -> list[tuple[ScalarNode, str]]:
    jobs = _one(root, "jobs")
    if not isinstance(jobs, MappingNode):
        raise WorkflowLintError("workflow 'jobs' must be a mapping")
    found: list[tuple[ScalarNode, str]] = []
    for _, job in jobs.value:
        reusable = _scalar(_one(job, "uses"), "uses")
        if reusable is not None:
            found.append((reusable, "workflow"))
        found.extend((reference, "action") for reference in _step_references(_one(job, "steps")))
    return found


def _composite_references(root: Node) -> list[tuple[ScalarNode, str]]:
    runs = _one(root, "runs")
    using = _scalar(_one(runs, "using") if runs else None, "using")
    if using is None or using.value != "composite":
        return []
    return [(reference, "action") for reference in _step_references(_one(runs, "steps"))]


def _target(root: Path, reference: str, kind: str) -> Path:
    if "@" in reference or not reference.startswith("$/"):
        raise WorkflowLintError(f"invalid same-repository reference: {reference!r}")
    relative = PurePosixPath(reference[2:])
    if relative.is_absolute() or not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise WorkflowLintError(f"invalid same-repository path: {reference!r}")
    target = (root / Path(*relative.parts)).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise WorkflowLintError(f"reference escapes the checkout: {reference!r}") from error
    if kind == "workflow":
        workflows = (root / ".github" / "workflows").resolve()
        if target.parent != workflows or target.suffix not in (".yml", ".yaml") or not target.is_file():
            raise WorkflowLintError(f"unsupported reusable workflow target: {reference!r}")
        return target
    metadata = [target / name for name in ("action.yml", "action.yaml") if (target / name).is_file()]
    if len(metadata) != 1:
        raise WorkflowLintError(f"action target needs exactly one metadata file: {reference!r}")
    return metadata[0]


def project(path: Path, root: Path, kind: str) -> tuple[bytes, list[Path]]:
    """Validate one YAML document and project its same-repository references."""
    source = path.read_text(encoding="utf-8")
    document = yaml.compose(source, Loader=yaml.SafeLoader)
    if document is None:
        raise WorkflowLintError(f"empty YAML document: {path}")
    ambiguous = _ambiguous_nodes(document)
    references = _workflow_references(document) if kind == "workflow" else _composite_references(document)
    offsets: list[int] = []
    targets: list[Path] = []
    for node, target_kind in references:
        if not node.value.startswith("$/"):
            continue
        if id(node) in ambiguous:
            raise WorkflowLintError(f"aliased same-repository reference in {path}")
        span = source[node.start_mark.index : node.end_mark.index]
        relative = span.find("$/")
        if relative < 0 or span.find("$/", relative + 1) >= 0:
            raise WorkflowLintError(f"ambiguous scalar spelling for {node.value!r}")
        offsets.append(node.start_mark.index + relative)
        targets.append(_target(root, node.value, target_kind))
    projected = source
    for offset in reversed(offsets):
        projected = projected[:offset] + "." + projected[offset + 1 :]
    return projected.encode("utf-8"), targets


def _git(root: Path, *arguments: str) -> str:
    result = process_tree.run(["git", *arguments], cwd=root, timeout=30)
    if result.returncode != 0:
        raise WorkflowLintError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout.decode("utf-8", "strict").strip()


def run(root: Path, candidate: str, actionlint: str) -> int:
    root = root.resolve()
    checkout = Path(_git(root, "rev-parse", "--show-toplevel")).resolve()
    if checkout != root or _git(root, "rev-parse", "HEAD") != candidate:
        raise WorkflowLintError("checkout does not match the declared candidate")
    if _git(root, "status", "--porcelain"):
        raise WorkflowLintError("candidate checkout is not clean")
    for analyzer in ("shellcheck", "pyflakes"):
        if shutil.which(analyzer) is None:
            raise WorkflowLintError(f"required actionlint analyzer is unavailable: {analyzer}")
    workflows = sorted((root / ".github" / "workflows").glob("*.y*ml"))
    queue: list[tuple[Path, str]] = [(path, "workflow") for path in workflows]
    queued = {path.resolve() for path in workflows}
    projected: dict[Path, bytes] = {}
    while queue:
        path, kind = queue.pop(0)
        content, targets = project(path, root, kind)
        if kind == "workflow":
            projected[path] = content
        for target in targets:
            workflows_root = (root / ".github" / "workflows").resolve()
            if target.suffix in (".yml", ".yaml") and target.parent != workflows_root and target.resolve() not in queued:
                queued.add(target.resolve())
                queue.append((target, "action"))
    failed = False
    for path, content in projected.items():
        result = process_tree.run(
            [actionlint, "-color", "-stdin-filename", str(path), "-"],
            cwd=root,
            input=content,
            timeout=300,
        )
        sys.stdout.buffer.write(result.stdout or b"")
        sys.stderr.buffer.write(result.stderr or b"")
        failed |= result.returncode != 0
    return int(failed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--actionlint", required=True)
    arguments = parser.parse_args()
    try:
        return run(arguments.root, arguments.candidate, arguments.actionlint)
    except (WorkflowLintError, yaml.YAMLError) as error:
        print(f"workflow lint: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

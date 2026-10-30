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


ACTIONLINT_CONFIGS = ("actionlint.yaml", "actionlint.yml")


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
    resolved = metadata[0].resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise WorkflowLintError(f"action metadata escapes the checkout: {reference!r}") from error
    if metadata[0].is_symlink():
        raise WorkflowLintError(f"action metadata must be a checkout file: {reference!r}")
    return resolved


def _project(source: bytes, path: Path, root: Path, kind: str) -> tuple[bytes, list[Path]]:
    try:
        text = source.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise WorkflowLintError(f"workflow is not UTF-8: {path}") from error
    document = yaml.compose(text, Loader=yaml.SafeLoader)
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
        span = text[node.start_mark.index : node.end_mark.index]
        relative = span.find("$/")
        if relative < 0 or span.find("$/", relative + 1) >= 0:
            raise WorkflowLintError(f"ambiguous scalar spelling for {node.value!r}")
        character_offset = node.start_mark.index + relative
        offsets.append(len(text[:character_offset].encode("utf-8")))
        targets.append(_target(root, node.value, target_kind))
    projected = bytearray(source)
    for offset in offsets:
        projected[offset] = ord(".")
    return bytes(projected), targets


def project(path: Path, root: Path, kind: str) -> tuple[bytes, list[Path]]:
    """Validate one YAML document and project its same-repository references."""
    return _project(path.read_bytes(), path, root, kind)


def _git(root: Path, *arguments: str) -> str:
    result = process_tree.run(["git", *arguments], cwd=root, timeout=30)
    if result.returncode != 0:
        raise WorkflowLintError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout.decode("utf-8", "strict").strip()


def _candidate_bytes(root: Path, candidate: str, path: Path) -> bytes:
    try:
        relative_path = path.relative_to(root)
        current = root
        for part in relative_path.parts:
            current /= part
            if current.is_symlink():
                raise WorkflowLintError(f"lint input uses a symlink: {path}")
        relative = path.resolve(strict=True).relative_to(root).as_posix()
    except (FileNotFoundError, ValueError) as error:
        raise WorkflowLintError(f"lint input escapes or is missing from the checkout: {path}") from error
    expected = process_tree.run(["git", "rev-parse", "--verify", f"{candidate}:{relative}"], cwd=root, timeout=30)
    if expected.returncode != 0:
        raise WorkflowLintError(f"lint input does not belong to candidate {candidate}: {relative}")
    actual = path.read_bytes()
    observed = process_tree.run(
        ["git", "hash-object", "--path", relative, "--stdin"], cwd=root, input=actual, timeout=30
    )
    if observed.returncode != 0 or observed.stdout.strip() != expected.stdout.strip():
        raise WorkflowLintError(f"lint input differs from candidate {candidate}: {relative}")
    return actual


def _collect(root: Path, candidate: str) -> tuple[dict[Path, bytes], dict[Path, bytes]]:
    configs = [root / ".github" / name for name in ACTIONLINT_CONFIGS if (root / ".github" / name).exists()]
    workflows = sorted((root / ".github" / "workflows").glob("*.y*ml"))
    queue: list[tuple[Path, str]] = [(path, "workflow") for path in workflows]
    queued = {path.resolve() for path in workflows}
    inputs = {path: _candidate_bytes(root, candidate, path) for path in configs}
    projected: dict[Path, bytes] = {}
    while queue:
        path, kind = queue.pop(0)
        source = _candidate_bytes(root, candidate, path)
        inputs[path] = source
        content, targets = _project(source, path, root, kind)
        if kind == "workflow":
            projected[path] = content
        for target in targets:
            source = _candidate_bytes(root, candidate, target)
            inputs[target] = source
            workflows_root = (root / ".github" / "workflows").resolve()
            if target.suffix in (".yml", ".yaml") and target.parent != workflows_root and target not in queued:
                queued.add(target)
                queue.append((target, "action"))
    return projected, inputs


def _verify_checkout(root: Path, candidate: str) -> None:
    checkout = Path(_git(root, "rev-parse", "--show-toplevel")).resolve()
    if checkout != root or _git(root, "rev-parse", "HEAD") != candidate:
        raise WorkflowLintError("checkout does not match the declared candidate")
    if _git(root, "status", "--porcelain"):
        raise WorkflowLintError("candidate checkout is not clean")


def run(root: Path, candidate: str, actionlint: str) -> int:
    root = root.resolve()
    _verify_checkout(root, candidate)
    for analyzer in ("shellcheck", "pyflakes"):
        if shutil.which(analyzer) is None:
            raise WorkflowLintError(f"required actionlint analyzer is unavailable: {analyzer}")
    projected, inputs = _collect(root, candidate)
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
    _verify_checkout(root, candidate)
    if _collect(root, candidate) != (projected, inputs):
        raise WorkflowLintError("candidate lint inputs changed during actionlint")
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

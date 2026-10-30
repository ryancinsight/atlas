"""Bind and lint Git candidate workflows byte-exactly."""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.tokens import ScalarToken

import process_tree

CONFIG_NAMES = ("actionlint.yaml", "actionlint.yml")
FULL_SHA = re.compile(r"[0-9a-f]{40}\Z")
STRING_TAG = "tag:yaml.org,2002:str"


class WorkflowSourceError(ValueError):
    """A workflow source is ambiguous, mutable, or outside its candidate."""


class WorkflowExecutionError(RuntimeError):
    """A required analyzer is unavailable or rejects the candidate."""


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
        relative = path.relative_to(root)
        current = root
        for part in relative.parts:
            entries = {entry.name for entry in os.scandir(current)}
            if part not in entries:
                raise FileNotFoundError(part)
            current /= part
            if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
                raise WorkflowSourceError(f"reference uses a path alias: {reference!r}")
        resolved = current.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, NotADirectoryError, ValueError) as error:
        raise WorkflowSourceError(f"reference escapes or is missing from the checkout: {reference!r}") from error
    return resolved


def _target(root: Path, reference: str, kind: str) -> Path:
    if "@" in reference or "\\" in reference or not reference.startswith(("$/", "./")):
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
    metadata = next(
        (target / name for name in ("action.yml", "action.yaml") if os.path.lexists(target / name)), None
    )
    if metadata is None:
        raise WorkflowSourceError(f"action target needs a metadata file: {reference!r}")
    resolved = _resolved(root, metadata, reference)
    if not resolved.is_file():
        raise WorkflowSourceError(f"action metadata must be a regular file: {reference!r}")
    return resolved


def _scalar_token(node: ScalarNode, tokens: list[ScalarToken], path: Path) -> ScalarToken:
    matches = [
        token
        for token in tokens
        if token.value == node.value
        and token.style == node.style
        and node.start_mark.index <= token.start_mark.index
        and token.end_mark.index == node.end_mark.index
    ]
    if len(matches) != 1:
        raise WorkflowSourceError(f"cannot locate scalar spelling in {path}")
    return matches[0]


def _sigil_offset(text: str, token: ScalarToken, path: Path) -> int:
    span = text[token.start_mark.index : token.end_mark.index]
    if token.style is None:
        relative = 0
    elif token.style in ("'", '"'):
        relative = 1
    else:
        header = span.find("\n")
        relative = header + 1
        while 0 < relative < len(span) and span[relative] in " \r\n":
            relative += 1
    if relative < 0 or not span.startswith("$/", relative):
        raise WorkflowSourceError(f"unsupported leading self-reference spelling in {path}")
    character = token.start_mark.index + relative
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
    tokens = [token for token in yaml.scan(text, Loader=yaml.SafeLoader) if isinstance(token, ScalarToken)]
    offsets: list[int] = []
    targets: list[Path] = []
    for node, target_kind in _references(document, kind):
        if node.value.startswith("./"):
            targets.append(_target(root, node.value, target_kind))
            continue
        if not node.value.startswith("$/"):
            continue
        if id(node) in ambiguous:
            raise WorkflowSourceError(f"aliased same-repository reference in {path}")
        offsets.append(_sigil_offset(text, _scalar_token(node, tokens, path), path))
        targets.append(_target(root, node.value, target_kind))
    projected = bytearray(source)
    for offset in offsets:
        projected[offset] = ord(".")
    return bytes(projected), targets


def _git(root: Path, *arguments: str) -> bytes:
    result = process_tree.run(["git", "--no-replace-objects", *arguments], cwd=root, timeout=30)
    if result.returncode != 0:
        raise WorkflowSourceError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def _identity(root: Path, candidate: str) -> str:
    if not FULL_SHA.fullmatch(candidate):
        raise WorkflowSourceError("candidate must be a full lowercase commit SHA")
    commit = _git(root, "rev-parse", "--verify", "--end-of-options", f"{candidate}^{{commit}}")
    checkout = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).absolute()
    head = _git(root, "rev-parse", "--verify", "HEAD").decode().strip()
    if commit.decode().strip() != candidate or checkout.as_posix() != root.as_posix() or head != candidate:
        raise WorkflowSourceError("checkout does not match the declared candidate")
    return _git(root, "rev-parse", f"{candidate}^{{tree}}").decode().strip()


def _checkout(root: Path, candidate: str) -> str:
    tree = _identity(root, candidate)
    if _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all"):
        raise WorkflowSourceError("candidate checkout is not clean")
    return tree


def _tree_paths(
    root: Path, candidate: str, recursive: bool, *paths: str
) -> tuple[tuple[str, str], ...]:
    arguments = ["ls-tree"]
    if recursive:
        arguments.append("-r")
    data = _git(root, *arguments, "-z", candidate, "--", *paths)
    entries = (
        (record.partition(b"\t")[2].decode("utf-8", "strict"), record.partition(b" ")[0].decode("ascii"))
        for record in data.split(b"\0")
        if record
    )
    return tuple(sorted(entries))


def _workflow_paths(root: Path) -> tuple[str, ...]:
    found: list[str] = []
    pending = [(root / ".github" / "workflows", ".github/workflows")]
    while pending:
        directory, prefix = pending.pop()
        for entry in os.scandir(directory):
            relative = f"{prefix}/{entry.name}"
            if entry.is_dir(follow_symlinks=False):
                pending.append((Path(entry.path), relative))
            elif entry.name.endswith((".yml", ".yaml")):
                found.append(relative)
    return tuple(sorted(found))


def _named_paths(root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(path for path in paths if os.path.lexists(root.joinpath(*path.split("/"))))


def _candidate_bytes(root: Path, candidate: str, relative: str, mode: str) -> bytes:
    if mode not in ("100644", "100755"):
        raise WorkflowSourceError(f"candidate input is not a regular Git file: {relative}")
    path = _resolved(root, root.joinpath(*relative.split("/")), relative)
    if not path.is_file():
        raise WorkflowSourceError(f"candidate input is not a regular file: {relative}")
    expected = _git(root, "cat-file", "blob", f"{candidate}:{relative}")
    source = path.read_bytes()
    if source != expected:
        raise WorkflowSourceError(f"lint input differs from candidate {candidate}: {relative}")
    return source


def _inventory(root: Path, candidate: str) -> tuple[tuple[str, str], ...]:
    workflows = tuple(
        entry
        for entry in _tree_paths(root, candidate, True, ".github/workflows")
        if entry[0].endswith((".yml", ".yaml"))
    )
    configs = tuple(f".github/{name}" for name in CONFIG_NAMES)
    candidate_configs = _tree_paths(root, candidate, False, *configs)
    working = _workflow_paths(root) + _named_paths(root, configs)
    candidate_entries = tuple(sorted(workflows + candidate_configs))
    if tuple(sorted(working)) != tuple(path for path, _ in candidate_entries):
        raise WorkflowSourceError("workflow or actionlint config inventory differs from candidate")
    return candidate_entries


def _metadata(root: Path, candidate: str, directory: str) -> tuple[tuple[str, str], ...]:
    names = tuple(f"{directory}/{name}" for name in ("action.yml", "action.yaml"))
    stored = dict(_tree_paths(root, candidate, False, *names))
    candidate_entries = tuple((name, stored[name]) for name in names if name in stored)
    if _named_paths(root, names) != tuple(name for name, _ in candidate_entries):
        raise WorkflowSourceError(f"action metadata inventory differs from candidate: {directory}")
    return candidate_entries


def _collect(
    root: Path, candidate: str, inventory: tuple[tuple[str, str], ...]
) -> tuple[dict[str, bytes], dict[str, bytes], tuple[tuple[str, str], ...]]:
    modes = dict(inventory)
    workflows = tuple(path for path in modes if path.startswith(".github/workflows/"))
    configs = tuple(f".github/{name}" for name in CONFIG_NAMES)
    selected_config = next((path for path in configs if path in modes), None)
    inputs = (
        {}
        if selected_config is None
        else {selected_config: _candidate_bytes(root, candidate, selected_config, modes[selected_config])}
    )
    pending = [(path, "workflow") for path in workflows]
    queued = set(workflows)
    projected: dict[str, bytes] = {}
    while pending:
        relative, kind = pending.pop(0)
        source = _candidate_bytes(root, candidate, relative, modes[relative])
        inputs[relative] = source
        content, targets = project(source, root.joinpath(*relative.split("/")), root, kind)
        if kind == "workflow":
            projected[relative] = content
        for target in targets:
            target_relative = target.relative_to(root).as_posix()
            if target_relative in workflows:
                continue
            directory = target.parent.relative_to(root).as_posix()
            for metadata, mode in _metadata(root, candidate, directory):
                modes[metadata] = mode
                inputs[metadata] = _candidate_bytes(root, candidate, metadata, mode)
                if metadata not in queued:
                    queued.add(metadata)
                    pending.append((metadata, "action"))
    return projected, inputs, tuple(sorted(modes.items()))


def snapshot(root: Path, candidate: str) -> tuple[dict[str, bytes], dict[str, bytes]]:
    """Collect projected workflows and every candidate-owned native lint input."""
    root = root.absolute()
    tree = _checkout(root, candidate)
    inventory = _inventory(root, candidate)
    first = _collect(root, candidate, inventory)
    if _checkout(root, candidate) != tree or _inventory(root, candidate) != inventory:
        raise WorkflowSourceError("candidate source changed while collecting lint inputs")
    if _collect(root, candidate, inventory) != first:
        raise WorkflowSourceError("candidate lint bytes changed while collecting inputs")
    if _checkout(root, candidate) != tree or _inventory(root, candidate) != inventory:
        raise WorkflowSourceError("candidate source changed after collecting lint inputs")
    if _collect(root, candidate, inventory) != first:
        raise WorkflowSourceError("candidate lint bytes changed during ending checks")
    if _identity(root, candidate) != tree or _inventory(root, candidate) != inventory:
        raise WorkflowSourceError("candidate source changed after ending byte checks")
    return first[0], first[1]


def _executable(value: str, name: str) -> str:
    resolved = shutil.which(value)
    if resolved is None:
        raise WorkflowExecutionError(f"required {name} executable is unavailable: {value}")
    return resolved


def _invoke(command: list[str], root: Path, source: bytes | None, timeout: float, name: str):
    try:
        return process_tree.run(command, cwd=root, input=source, timeout=timeout)
    except process_tree.ProcessTreeTimeout as error:
        raise WorkflowExecutionError(f"{name} exceeded its {timeout:g}-second deadline") from error
    except (OSError, RuntimeError) as error:
        raise WorkflowExecutionError(f"cannot execute {name}: {error}") from error


def _output(result) -> str:
    return b"\n".join(part for part in (result.stdout, result.stderr) if part).decode("utf-8", "replace").strip()


def run(
    root: Path,
    candidate: str,
    actionlint: str,
    shellcheck: str = "shellcheck",
    pyflakes: str = "pyflakes",
    timeout: float = 30,
) -> None:
    """Run actionlint against every projected workflow in an immutable candidate."""
    root = root.absolute()
    tools = (
        _executable(actionlint, "actionlint"),
        _executable(shellcheck, "shellcheck"),
        _executable(pyflakes, "pyflakes"),
    )
    initial = snapshot(root, candidate)
    failure: WorkflowExecutionError | None = None
    try:
        version = _invoke([tools[0], "-version"], root, None, timeout, "actionlint")
        first_line = (version.stdout or b"").decode("utf-8", "replace").splitlines()
        if version.returncode != 0 or first_line[:1] != ["1.7.12"]:
            failure = WorkflowExecutionError(f"actionlint must be version 1.7.12: {_output(version)}")
        else:
            diagnostics: list[str] = []
            for relative, source in initial[0].items():
                result = _invoke(
                    [
                        tools[0],
                        "-no-color",
                        "-shellcheck",
                        tools[1],
                        "-pyflakes",
                        tools[2],
                        "-stdin-filename",
                        str(root.joinpath(*relative.split("/"))),
                        "-",
                    ],
                    root,
                    source,
                    timeout,
                    "actionlint",
                )
                if result.returncode != 0:
                    diagnostics.append(_output(result))
            if diagnostics:
                failure = WorkflowExecutionError("actionlint rejected the candidate:\n" + "\n".join(diagnostics))
    except WorkflowExecutionError as error:
        failure = error
    ending = snapshot(root, candidate)
    if ending != initial:
        raise WorkflowSourceError("candidate lint inputs changed during actionlint")
    if failure is not None:
        raise failure


def main() -> int:
    """Parse the command line and report typed source or analyzer failures."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--actionlint", required=True)
    parser.add_argument("--shellcheck", default="shellcheck")
    parser.add_argument("--pyflakes", default="pyflakes")
    parser.add_argument("--timeout", default=30, type=float)
    arguments = parser.parse_args()
    try:
        run(
            arguments.root,
            arguments.candidate,
            arguments.actionlint,
            arguments.shellcheck,
            arguments.pyflakes,
            arguments.timeout,
        )
    except (WorkflowSourceError, WorkflowExecutionError, yaml.YAMLError) as error:
        print(f"workflow lint: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

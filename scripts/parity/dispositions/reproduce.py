"""Replay bounded source evidence from captured inputs; no network or framework imports."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY / "scripts"))
from atlas_parity import load

DATA = REPOSITORY / "docs/parity/reference/closure"
CAPTURES = {"jax-selection": "atlas-parity-jax-selection",
            "torch-new-tensor": "atlas-parity-torch-new-tensor",
            "keras-saving": "atlas-parity-keras-saving-closure",
            "numpy-ufunc": "atlas-parity-numpy-ufunc-expansion"}
SCRIPTS = {"jax-selection": ["selection.py", "test_selection.py"],
           "torch-new-tensor": ["source_contract.py", "acceptance_cases.py", "test_source_contract.py"],
           "keras-saving": ["inspect_wheel.py", "build_resolution.py", "machine_assertions.py"],
           "numpy-ufunc": ["expand_ufuncs.py", "validate_expansion.py", "test_ufunc_expansion.py"]}
STABLE = {"jax-selection": ["selection-dispositions.json"],
          "torch-new-tensor": ["contract.json", "acceptance-cases.json"],
          "keras-saving": ["saving-endpoint-resolution.json", "packaged-module-exports.json",
                           "record-verification.json", "git-source-verification.json", "assertion-results.json"],
          "numpy-ufunc": ["bounded-completeness.json", "documentation-dispositions.json", "ufunc-bindings.json",
                          "ufunc-expansions.json", "ufunc-members.json", "ufunc-objects.json"]}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed(source, destination, expected):
    if not destination.exists():
        if not source.is_file():
            raise ValueError(f"Missing captured primary input: {source}; source receipt required")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    if digest(destination) != expected:
        raise ValueError(f"Captured input differs from versioned source receipt: {destination}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", choices=CAPTURES)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--capture-cache", type=Path)
    parser.add_argument("--source-cache", type=Path)
    args = parser.parse_args()
    load()  # Verify canonical artifact hashes, frozen baselines and scope first.
    group = args.group
    canonical = DATA / group
    capture = (args.capture_cache or Path("/tmp") / CAPTURES[group]).resolve()
    work = (args.work or Path(str(capture) + "-replay")).resolve()
    if work == capture or work.is_relative_to(REPOSITORY):
        raise ValueError("Choose an external replay directory separate from the original capture")
    work.mkdir(parents=True, exist_ok=True)
    for source in canonical.rglob("*.json"):
        seed(source, work / source.relative_to(canonical), digest(source))
    if group == "jax-selection":
        sources = json.loads((canonical / "tooling-sources.json").read_text(encoding="utf-8"))["sources"]
        for row in sources:
            seed(capture / row["path"], work / row["path"], row["sha256"])
        source_cache = (args.source_cache or Path("/tmp/atlas-numpy-jax-parity/jax")).resolve()
        for row in json.loads((canonical / "selection-dispositions.json").read_text(encoding="utf-8"))["jax_sources"]:
            if digest(source_cache / row["path"]) != row["sha256"]:
                raise ValueError("Frozen JAX source drift: " + row["path"])
    elif group == "torch-new-tensor":
        for row in json.loads((canonical / "sources.json").read_text(encoding="utf-8")):
            seed(capture / "sources" / row["path"], work / "sources" / row["path"], row["sha256"])
        source_cache = (args.source_cache or Path("/tmp/atlas-parity-torch-closure")).resolve()
    elif group == "numpy-ufunc":
        manifest = json.loads((canonical / "handoff-manifest.json").read_text(encoding="utf-8"))
        for row in manifest["files"]:
            if row["path"].startswith(("sources/", "inputs/", "comparison-source/")):
                seed(capture / row["path"], work / row["path"], row["sha256"])
        source_cache = (args.source_cache or Path("/tmp/atlas-parity-numpy-closure")).resolve()
    else:
        manifest = json.loads((canonical / "manifest.json").read_text(encoding="utf-8"))
        for row in manifest["artifacts"]:
            name = row["file"]
            if name.startswith(("official-docs/", "source-witnesses/")) or name == manifest["wheel"]["filename"]:
                seed(capture / name, work / name, row["sha256"])
        source_cache = (args.source_cache or Path("/tmp/atlas-parity-tf-closure")).resolve()
    environment = dict(os.environ, ATLAS_REFERENCE_REPOSITORY=str(REPOSITORY),
                       ATLAS_REFERENCE_SOURCE_CACHE=str(source_cache),
                       ATLAS_REFERENCE_BASE_CACHE=str(source_cache),
                       ATLAS_REFERENCE_BASE_CLOSURE=str(DATA / "torch"),
                       ATLAS_REFERENCE_PRIOR_JAX_ADDITIONS=str(DATA / "jax/review-ready-additions.json"),
                       ATLAS_REFERENCE_OFFLINE="1")
    for source in (Path(__file__).parent / group).glob("*.py"):
        shutil.copyfile(source, work / source.name)
    for name in SCRIPTS[group]:
        subprocess.run([sys.executable, str(work / name)], cwd=work, env=environment, check=True, timeout=60)
    for name in STABLE[group]:
        if digest(work / name) != digest(canonical / name):
            raise ValueError("Reproduced source fact differs from canonical capture: " + name)
    print(json.dumps({"group": group, "stable_source_outputs": len(STABLE[group]),
                      "framework_imports": False, "runtime_parity_verification": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

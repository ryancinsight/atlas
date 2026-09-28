#!/usr/bin/env python3
"""Shared fixtures for build identity tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "atlas_build_identity.py"
SPEC = importlib.util.spec_from_file_location("atlas_build_identity", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
sys.path.insert(0, str(SCRIPT.parent))
import atlas_build_artifacts as artifacts
import atlas_build_source as source
import atlas_build_record as records
from atlas_build_lease import (
    BuildIdentityError,
    OwnerLease,
    lease_is_held,
    package_target_lease_path,
)
from atlas_build_target import TargetDirectory

identity = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = identity
SPEC.loader.exec_module(identity)

import atlas_build_run as build_workflow
import atlas_build_check as check_workflow

def artifact_record(files: dict[str, str]) -> dict[str, object]:
    digest = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {"files": files, "digest": digest}

def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.stdout.strip()

def init_repo(root: Path, source: str) -> None:
    root.mkdir(parents=True)
    (root / "Cargo.toml").write_bytes(
        b"[package]\nname = \"demo\"\nversion = \"0.1.0\"\n"
    )
    (root / "Cargo.lock").write_bytes(
        b"version = 4\n\n[[package]]\nname = \"demo\"\nversion = \"0.1.0\"\n"
    )
    (root / "src").mkdir()
    (root / "src/lib.rs").write_bytes(source.encode("utf-8"))
    git(root, "init", "-q")
    git(root, "config", "core.autocrlf", "false")
    git(root, "config", "user.name", "Atlas test")
    git(root, "config", "user.email", "atlas-test@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "source")

def write_script(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")

class BuildIdentityFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "source-a"
        self.target = self.base / "shared-target"
        self.artifact = self.target / "debug" / "deps" / "libdemo-abcdef.rlib"
        self.artifact.parent.mkdir(parents=True)
        self.clean_log = self.base / "clean.log"
        self.build_script = self.base / "build.py"
        self.clean_script = self.base / "clean.py"
        write_script(
            self.build_script,
            "import os\n"
            "from pathlib import Path\n"
            "path = Path(os.environ['ARTIFACT'])\n"
            "path.parent.mkdir(parents=True, exist_ok=True)\n"
            "path.write_text(os.environ['SOURCE_TOKEN'], encoding='utf-8')\n"
            "mutate = os.environ.get('MUTATE_SOURCE')\n"
            "if mutate:\n"
            "    Path(mutate).write_text('changed during build\\n', encoding='utf-8')\n",
        )
        write_script(
            self.clean_script,
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['CLEAN_LOG']).write_text('cleaned\\n', encoding='utf-8')\n"
            "Path(os.environ['ARTIFACT']).unlink(missing_ok=True)\n",
        )

    def build(
        self,
        root: Path | None = None,
        source_token: str = "source-a",
        **options: object,
    ) -> build_workflow.BuildResult:
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.dict(
                os.environ,
                {
                    "ARTIFACT": str(self.artifact),
                    "SOURCE_TOKEN": source_token,
                    "CLEAN_LOG": str(self.clean_log),
                },
            ),
        ):
            return build_workflow.run_build(
                root or self.root,
                (root or self.root) / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(self.build_script)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, str(self.clean_script)],
                **options,
            )


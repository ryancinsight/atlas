"""Removal of directory trees whose entries may be read-only, for test fixtures."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def clear_readonly_tree(path: Path) -> None:
    """Remove a tree whose entries may be read-only (a clone's object files, the gate's exports).

    `shutil.rmtree(onexc=)` is 3.12+ and the hosted runners hold 3.11, so the
    entries are made writable first and removed with the version-agnostic
    plain form.
    """
    # A fixture link owns only the link, never its target (which may be absent
    # or outside this tree). chmod follows links, whereas rmtree removes them.
    if path.is_symlink():
        path.unlink()
        return
    if not path.exists():
        return
    for root, dirs, files in os.walk(path):
        for name in (root, *(os.path.join(root, entry) for entry in dirs + files)):
            if not os.path.islink(name):
                os.chmod(name, 0o700)
    shutil.rmtree(path)

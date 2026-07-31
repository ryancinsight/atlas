"""Smoke tests for building Atlas mdBooks."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.book_build
@pytest.mark.slow
def test_kwavers_mdbook_builds() -> None:
    """Verify that the kwavers mdBook builds without errors."""
    book_dir = REPO_ROOT / "repos" / "kwavers" / "docs" / "book"
    if not book_dir.exists():
        pytest.skip(f"Book directory not found: {book_dir}")

    mdbook = shutil.which("mdbook")
    if mdbook is None:
        pytest.skip("mdbook executable not found on PATH")

    with tempfile.TemporaryDirectory(prefix="mdbook-build-") as dest:
        result = subprocess.run(
            [mdbook, "build", str(book_dir), "--dest-dir", dest],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"mdbook build failed:\n{result.stderr}"
        assert (Path(dest) / "index.html").exists(), "mdbook build did not produce index.html"

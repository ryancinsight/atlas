"""Session setup for the scripts test suite."""

import os

import pytest

from atlas_git_process import clean_process_env


_SLOW_SOURCE_BUILD_PREFIXES = (
    "scripts/tests/test_atlas_semver_locked.py::NativeContract::",
    "scripts/tests/test_semver_tool.py::PreparedCheckerContract::",
)


def pytest_collection_modifyitems(items):
    """Keep exact-source checker builds out of the parallel fast partition."""
    for item in items:
        if item.nodeid.startswith(_SLOW_SOURCE_BUILD_PREFIXES):
            item.add_marker(pytest.mark.slow)

# Fixtures build throwaway repositories and commit in them. A GIT_DIR,
# GIT_WORK_TREE or GIT_INDEX_FILE inherited from the caller -- a pre-push
# hook, or an agent driving a private index -- redirects those commits into
# the caller's repository instead.
for _key in os.environ.keys() - clean_process_env().keys():
    del os.environ[_key]

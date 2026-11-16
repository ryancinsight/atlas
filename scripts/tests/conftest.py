"""Session setup for the scripts test suite."""

import os

from atlas_git_process import clean_process_env

# Fixtures build throwaway repositories and commit in them. A GIT_DIR,
# GIT_WORK_TREE or GIT_INDEX_FILE inherited from the caller -- a pre-push
# hook, or an agent driving a private index -- redirects those commits into
# the caller's repository instead.
for _key in os.environ.keys() - clean_process_env().keys():
    del os.environ[_key]

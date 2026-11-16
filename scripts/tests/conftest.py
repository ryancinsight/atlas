"""Session setup for the scripts test suite."""

import os

from atlas_git_process import clean_process_env

# Fixtures build throwaway repositories and commit in them. A GIT_DIR,
# GIT_WORK_TREE or GIT_INDEX_FILE inherited from the caller -- a pre-push
# hook, or an agent driving a private index -- redirects those commits into
# the caller's repository instead.
for _key in os.environ.keys() - clean_process_env().keys():
    del os.environ[_key]

# Fixtures delete their throwaway repositories as soon as a test ends, while
# a `commit` or `fetch` may have started Git's detached auto maintenance
# (`gc --auto`, `maintenance run --auto`), which writes `objects/
# maintenance.lock` and packs into the same tree. Teardown then races it
# (FileNotFoundError on `maintenance.lock` in CI run 43831637889). Settings in
# `GIT_CONFIG_PARAMETERS` apply to every git the suite starts, and
# `clean_process_env` passes them through.
_MAINTENANCE_OFF = "'gc.auto=0' 'maintenance.auto=false' 'receive.autogc=false'"
os.environ["GIT_CONFIG_PARAMETERS"] = " ".join(
    entry for entry in (os.environ.get("GIT_CONFIG_PARAMETERS"), _MAINTENANCE_OFF) if entry
)

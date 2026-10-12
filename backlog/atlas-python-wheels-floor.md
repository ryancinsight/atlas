<a id="atlas-python-wheels-floor"></a>
## ATLAS-PYTHON-WHEELS-FLOOR - Shared wheel workflow admits a Python floor its test step cannot install [verification] - todo
- priority: verification; needs: none; scope: `.github/workflows/python-wheels.yml`, `scripts/tests/`, `repos/apollo/.github/workflows/python-release.yml`
- evidence (2026-10-12): cfdrs-python's first release (CFDrs run 38263015633) failed macOS/Windows abi3 jobs at `pip install pytest==8.4.2` under Python 3.8 (pytest 8.4 needs >=3.9); CFDrs#538 moved to abi3-py39. apollo still sets `abi3-python: "3.8"`; verification-mode callers must grant `contents: write` to a run that writes nothing.
- acceptance: an `abi3-python` below the pinned pytest's floor fails input validation naming the floor; verification mode holds `contents: read`; apollo moves to a supported floor.

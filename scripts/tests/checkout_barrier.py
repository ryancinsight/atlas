"""Post-checkout barrier shared by the real Git materialization fixtures."""

import json
import os
from pathlib import Path
import time


def publish_marker(folder: Path, record: dict) -> None:
    marker = folder / str(record["pid"])
    staged = folder / f".{marker.name}.pending"
    try:
        with staged.open("w", encoding="utf-8") as stream:
            json.dump(record, stream)
        # Readers treat numeric names as complete packets. Publish only after
        # the stream closes, in one rename on the same filesystem.
        staged.replace(marker)
    finally:
        staged.unlink(missing_ok=True)


def main() -> None:
    folder = Path(os.environ["MATERIALIZATION_BARRIER"])
    path = Path.cwd()
    publish_marker(folder, {"pid": os.getpid(), "path": str(path)})
    while not (folder / "release").exists() and not (folder / path.name).exists():
        time.sleep(0.02)
    if path.name == os.environ.get("MATERIALIZATION_FAIL", ""):
        raise SystemExit(42)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Deploy this repo's skill files into the runtime Hermes skill directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = Path.home() / ".hermes" / "skills" / "productivity" / "google-workspace-multi-account"
INCLUDE_PATHS = [
    "SKILL.md",
    "references",
    "scripts",
]
EXCLUDE_NAMES = {
    "__pycache__",
    ".DS_Store",
}
EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def _copy_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for child in src.iterdir():
            if child.name in EXCLUDE_NAMES or child.suffix in EXCLUDE_SUFFIXES:
                continue
            _copy_path(child, dst / child.name)
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def deploy(dest: Path) -> list[str]:
    copied: list[str] = []
    dest.mkdir(parents=True, exist_ok=True)
    for relative in INCLUDE_PATHS:
        src = PROJECT_ROOT / relative
        if not src.exists():
            continue
        if src.is_dir():
            target_dir = dest / relative
            if target_dir.exists():
                shutil.rmtree(target_dir)
            _copy_path(src, target_dir)
        else:
            _copy_path(src, dest / relative)
        copied.append(relative)
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy repo skill files to runtime Hermes skills directory")
    parser.add_argument("--dest", default=str(DEFAULT_DEST), help="Target runtime skill directory")
    args = parser.parse_args()

    dest = Path(args.dest).expanduser().resolve()
    copied = deploy(dest)
    print("Deployed:")
    for item in copied:
        print(f"- {item}")
    print(f"Destination: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

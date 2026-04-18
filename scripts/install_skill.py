#!/usr/bin/env python3
"""Install this skill into a local Hermes runtime directory."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
DEFAULT_DEST = DEFAULT_HERMES_HOME / "skills" / "productivity" / "google-workspace-multi-account"
DEFAULT_PYTHON = DEFAULT_HERMES_HOME / "hermes-agent" / "venv" / "bin" / "python"


def main() -> int:
    parser = argparse.ArgumentParser(description="Install google-workspace-multi-account into a Hermes runtime")
    parser.add_argument("--hermes-home", default=str(DEFAULT_HERMES_HOME), help="Hermes home directory (default: ~/.hermes)")
    parser.add_argument("--python", default=str(DEFAULT_PYTHON), help="Python interpreter to use for deployment")
    args = parser.parse_args()

    hermes_home = Path(args.hermes_home).expanduser().resolve()
    python_bin = Path(args.python).expanduser().resolve()
    deploy_script = PROJECT_ROOT / "scripts" / "deploy_skill.py"
    dest = hermes_home / "skills" / "productivity" / "google-workspace-multi-account"

    if not python_bin.exists():
        print(f"ERROR: Python interpreter not found: {python_bin}", file=sys.stderr)
        return 1
    if not deploy_script.exists():
        print(f"ERROR: Deploy script not found: {deploy_script}", file=sys.stderr)
        return 1

    cmd = [str(python_bin), str(deploy_script), "--dest", str(dest)]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        return result.returncode

    print("\nInstall complete.")
    print(f"Hermes home: {hermes_home}")
    print(f"Skill path:   {dest}")
    print("Next step: connect an account with setup_multi.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

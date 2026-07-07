#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"classic", "docker"}:
        print("Usage: python scripts/switch_readme.py [classic|docker]")
        return 1

    variant = sys.argv[1]
    repo_root = Path(__file__).resolve().parents[1]
    source = repo_root / f"README.{variant}.md"
    target = repo_root / "README.md"

    if not source.exists():
        print(f"README variant not found: {source}")
        return 1

    shutil.copyfile(source, target)
    print(f"Switched README.md to '{variant}' variant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

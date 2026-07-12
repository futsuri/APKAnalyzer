#!/usr/bin/env python3
"""Тонкая обёртка для обратной совместимости.

Делегирует к main.py --mode dynamic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Динамический анализ APK (обёртка)')
    parser.add_argument('apk', help='Путь к APK файлу')
    parser.add_argument('--package', required=True, help='Package name')
    parser.add_argument('--emulator-host', default=None, help='Хост эмулятора')
    parser.add_argument('--container', default=None, help='[deprecated] игнорируется, используйте --emulator-host')

    args = parser.parse_args()

    # Делегируем в main.py
    from main import main as cli_main

    sys.argv = [
        "main.py",
        args.apk,
        "--mode", "dynamic",
        "--package", args.package,
    ]
    if args.emulator_host:
        sys.argv.extend(["--emulator-host", args.emulator_host])

    cli_main()


if __name__ == "__main__":
    main()

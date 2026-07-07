#!/usr/bin/env python3
"""
APK Analyzer - CLI инструмент для анализа Android APK
"""

import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.apk_service import ApkService
from src.core.config import STATIC_OUTPUT_DIR
from src.static.reporters.report_generator import ReportGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Анализ APK файлов')
    parser.add_argument('apk', help='Путь к APK файлу')
    parser.add_argument('--output', '-o', help='Директория для отчётов')
    parser.add_argument('--debug', action='store_true', help='Включить debug логирование')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    apk_path = Path(args.apk)
    if not apk_path.exists():
        logger.error(f"APK файл не найден: {apk_path}")
        sys.exit(1)

    output_dir = Path(args.output) if args.output else STATIC_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Начинаем анализ: {apk_path}")

    service = ApkService(apk_path)

    try:
        result = service.analyze_simple()

        # Сохранение отчетов во всех форматах
        ReportGenerator.save_report(result, output_dir, formats=["md", "json", "html"])
        
        logger.info(f"✅ Markdown отчёт: {output_dir / f'{apk_path.stem}_report.md'}")
        logger.info(f"✅ JSON отчёт: {output_dir / f'{apk_path.stem}_report.json'}")
        logger.info(f"✅ HTML отчёт: {output_dir / f'{apk_path.stem}_report.html'}")

        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТЫ АНАЛИЗА")
        print("=" * 60)
        print(f"APK: {apk_path.name}")
        
        manifest = result.manifest
        if manifest:
            print(f"Package: {manifest.package}")
            print(f"Version: {manifest.version_name}")
            print(f"Разрешений: {len(manifest.permissions)}")
        
        identifiers = result.identifiers
        found = sum(1 for data in identifiers.values() if data.found)
        total = len(identifiers)
        print(f"Идентификаторов найдено: {found}/{total}")
        print(f"Секретов найдено: {len(result.secrets)}")
        print(f"Библиотек: {len(result.libraries)}")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        service.cleanup()


if __name__ == '__main__':
    main()
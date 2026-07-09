#!/usr/bin/env python3
import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

from dynamic.orchestrator import DynamicOrchestrator


def main():
    parser = argparse.ArgumentParser(description='Динамический анализ APK')
    parser.add_argument('apk', help='Путь к APK файлу')
    parser.add_argument('--package', required=True, help='Package name приложения')
    parser.add_argument('--container', default='android-emulator', help='Имя Docker-контейнера')
    args = parser.parse_args()

    apk_path = Path(args.apk)
    if not apk_path.exists():
        logger.error(f"❌ APK не найден: {apk_path}")
        sys.exit(1)

    logger.info("=" * 80)
    logger.info("🚀 ЗАПУСК ДИНАМИЧЕСКОГО АНАЛИЗА")
    logger.info(f"📱 APK: {apk_path}")
    logger.info(f"📦 Package: {args.package}")
    logger.info("=" * 80)

    orchestrator = DynamicOrchestrator(container_name=args.container)
    result = orchestrator.run_analysis(apk_path, args.package)
    orchestrator.save_results(Path('results/dynamic'))

    print("\n" + "=" * 60)
    print("🔍 НАЙДЕННЫЕ ИДЕНТИФИКАТОРЫ:")
    if result['identifiers']:
        for id_item in result['identifiers']:
            print(f"  - {id_item['type']}: {id_item['value']}")
    else:
        print("  ❌ Идентификаторы не найдены")

    if result['errors']:
        print("\n⚠️ ОШИБКИ:")
        for err in result['errors']:
            print(f"  - {err}")
    print("=" * 60)


if __name__ == "__main__":
    main()
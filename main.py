#!/usr/bin/env python3
"""
APK Analyzer - CLI инструмент для анализа Android APK.

Режимы:
  static  — статический анализ (decompile + поиск идентификаторов/секретов)
  dynamic — динамический анализ (Frida-хуки на эмуляторе)
  full    — статический + динамический
"""

import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import STATIC_OUTPUT_DIR, DYNAMIC_OUTPUT_DIR
from src.services.apk_service import ApkService
from src.static.reporters.report_generator import ReportGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _run_static(apk_path: Path, output_dir: Path):
    """Запускает статический анализ."""
    service = ApkService(apk_path)
    try:
        result = service.analyze_simple()
        ReportGenerator.save_report(result, output_dir, formats=["md", "json", "html"])
        logger.info("Статические отчёты сохранены в: %s", output_dir)
        return result
    finally:
        service.cleanup()


def _run_dynamic(apk_path: Path, package_name: str, emulator_host, output_dir: Path):
    """Запускает динамический анализ."""
    from src.dynamic.orchestrator import DynamicOrchestrator
    from src.models.analysis import AnalysisResult

    orchestrator = DynamicOrchestrator(emulator_host=emulator_host)
    dyn_result = orchestrator.run(apk_path, package_name)

    # Оборачиваем в AnalysisResult для ReportGenerator
    analysis = AnalysisResult(
        apk_file=apk_path.name,
        identifiers=dyn_result.findings,
    )
    analysis.summary = {
        "apk_file": apk_path.name,
        "package": package_name,
        "mode": "dynamic",
        "identifiers_found": sum(1 for f in dyn_result.findings.values() if f.found),
        "identifiers_total": len(dyn_result.findings),
        "errors": dyn_result.errors,
    }

    ReportGenerator.save_report(analysis, output_dir, formats=["md", "json", "html"])
    logger.info("Динамические отчёты сохранены в: %s", output_dir)

    return dyn_result


def _print_summary(mode, static_result=None, dynamic_result=None):
    """Выводит итоговую сводку в консоль."""
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ АНАЛИЗА")
    print("=" * 60)
    print(f"Режим: {mode}")

    if static_result:
        print(f"APK: {static_result.apk_file}")
        if static_result.manifest:
            print(f"Package: {static_result.manifest.package}")
            print(f"Version: {static_result.manifest.version_name}")
            print(f"Разрешений: {len(static_result.manifest.permissions)}")
        found = sum(1 for data in static_result.identifiers.values() if data.found)
        total = len(static_result.identifiers)
        print(f"Идентификаторов (static): {found}/{total}")
        print(f"Секретов: {len(static_result.secrets)}")
        print(f"Библиотек: {len(static_result.libraries)}")

    if dynamic_result:
        found = sum(1 for f in dynamic_result.findings.values() if f.found)
        total = len(dynamic_result.findings)
        print(f"Идентификаторов (dynamic): {found}/{total}")
        if dynamic_result.raw_values_path:
            print(f"Немаскированные значения: {dynamic_result.raw_values_path}")
        if dynamic_result.errors:
            print(f"Ошибки: {len(dynamic_result.errors)}")
            for err in dynamic_result.errors:
                print(f"  - {err}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Анализ APK файлов')
    parser.add_argument('apk', help='Путь к APK файлу')
    parser.add_argument('--output', '-o', help='Директория для отчётов')
    parser.add_argument('--debug', action='store_true', help='Включить debug логирование')
    parser.add_argument('--mode', choices=['static', 'dynamic', 'full'], default='static',
                        help='Режим анализа (default: static)')
    parser.add_argument('--package', help='Package name (обязателен для dynamic/full)')
    parser.add_argument('--emulator-host', help='Хост эмулятора (default: EMULATOR_HOST или android-emulator)')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    apk_path = Path(args.apk)
    if not apk_path.exists():
        logger.error("APK файл не найден: %s", apk_path)
        sys.exit(1)

    # Валидация аргументов для dynamic
    if args.mode in ("dynamic", "full") and not args.package:
        logger.error("--package обязателен для режима %s", args.mode)
        sys.exit(1)

    static_output = Path(args.output) if args.output else STATIC_OUTPUT_DIR
    dynamic_output = Path(args.output) if args.output else DYNAMIC_OUTPUT_DIR

    static_result = None
    dynamic_result = None

    # --- Static ---
    if args.mode in ("static", "full"):
        try:
            static_result = _run_static(apk_path, static_output)
        except Exception as e:
            logger.error("Ошибка статического анализа: %s", e)
            import traceback
            traceback.print_exc()
            if args.mode == "static":
                sys.exit(1)

    # --- Dynamic ---
    if args.mode in ("dynamic", "full"):
        try:
            dynamic_result = _run_dynamic(
                apk_path, args.package, args.emulator_host, dynamic_output,
            )
        except Exception as e:
            logger.error("Ошибка динамического анализа: %s", e)
            import traceback
            traceback.print_exc()
            if args.mode == "dynamic":
                sys.exit(1)

    _print_summary(args.mode, static_result, dynamic_result)


if __name__ == '__main__':
    main()

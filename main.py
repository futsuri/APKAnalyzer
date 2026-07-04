#!/usr/bin/env python3
"""
APK Analyzer - CLI инструмент для анализа Android APK
"""

import sys
import logging
import argparse
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.services.apk_service import ApkService
from src.core.config import STATIC_OUTPUT_DIR, DYNAMIC_OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_markdown_report(result, apk_name):
    lines = []
    lines.append(f"# Анализ APK: {apk_name}")
    lines.append(f"**Дата анализа:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("---\n")

    if result.get('manifest'):
        m = result['manifest']
        lines.append("## Информация о приложении")
        lines.append(f"- **Package:** `{m.get('package', 'unknown')}`")
        lines.append(f"- **Version:** `{m.get('version_name', 'unknown')}` ({m.get('version_code', '0')})")
        lines.append(f"- **Target SDK:** `{m.get('target_sdk', 0)}`")
        lines.append(f"- **Min SDK:** `{m.get('min_sdk', 0)}`\n")

        lines.append("## Разрешения (Permissions)")
        if m.get('permissions'):
            dangerous = [p for p in m['permissions'] if p.get('is_dangerous')]
            lines.append(f"**Всего разрешений:** {len(m['permissions'])}")
            lines.append(f"**Опасных:** {len(dangerous)}\n")
            lines.append("### Все разрешения")
            for p in m['permissions']:
                danger = "⚠️" if p.get('is_dangerous') else "✅"
                lines.append(f"- {danger} `{p['name']}`")
        else:
            lines.append("Разрешения не найдены\n")

    lines.append("\n## Использование идентификаторов устройства")
    if result.get('identifiers'):
        for name, data in result['identifiers'].items():
            if data.get('found'):
                lines.append(f"\n### ✅ {name} **найден**")
                if data.get('locations'):
                    lines.append("**Найден в:**")
                    for loc in data['locations'][:5]:
                        lines.append(f"- `{loc.get('file', 'unknown')}` (строка {loc.get('line', '?')})")
            else:
                lines.append(f"\n### ❌ {name} **не найден**")
    else:
        lines.append("Идентификаторы не анализировались\n")

    lines.append("\n## Секреты")
    if result.get('secrets'):
        lines.append(f"**Найдено секретов:** {len(result['secrets'])}")
        types = {}
        for secret in result['secrets']:
            t = secret.get('type', 'unknown')
            types[t] = types.get(t, 0) + 1
        lines.append("\n**Типы секретов:**")
        for t, count in types.items():
            lines.append(f"- {t}: {count}")
        lines.append("\n**Примеры (первые 10):**")
        for secret in result['secrets'][:10]:
            lines.append(f"- **{secret.get('type', 'unknown')}:** `{secret.get('value', '')[:50]}`")
    else:
        lines.append("Секреты не найдены ✅")

    lines.append("\n## Используемые библиотеки")
    if result.get('libraries'):
        for lib in sorted(result['libraries'])[:20]:
            lines.append(f"- `{lib}`")
        if len(result['libraries']) > 20:
            lines.append(f"\n*... и ещё {len(result['libraries']) - 20} библиотек*")
    else:
        lines.append("Библиотеки не определены")

    lines.append("\n## Резюме")
    lines.append(f"- **APK:** `{result.get('apk_file', apk_name)}`")
    if result.get('manifest'):
        lines.append(f"- **Package:** `{result['manifest'].get('package', 'unknown')}`")
        lines.append(f"- **Version:** `{result['manifest'].get('version_name', 'unknown')}`")
    
    identifiers = result.get('identifiers', {})
    found = sum(1 for data in identifiers.values() if data.get('found'))
    total = len(identifiers)
    lines.append(f"- **Идентификаторы найдены:** {found}/{total}")
    lines.append(f"- **Секреты найдены:** {len(result.get('secrets', []))}")
    lines.append(f"- **Библиотек обнаружено:** {len(result.get('libraries', []))}")

    return "\n".join(lines)


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
        result_dict = service.analyze_simple()

        md_content = generate_markdown_report(result_dict, apk_path.name)
        md_path = output_dir / f"{apk_path.stem}_report.md"
        md_path.write_text(md_content, encoding='utf-8')
        logger.info(f"✅ Markdown отчёт: {md_path}")

        json_path = output_dir / f"{apk_path.stem}_report.json"
        json_path.write_text(json.dumps(result_dict, indent=2, default=str, ensure_ascii=False), encoding='utf-8')
        logger.info(f"✅ JSON отчёт: {json_path}")

        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТЫ АНАЛИЗА")
        print("=" * 60)
        print(f"APK: {apk_path.name}")
        
        manifest = result_dict.get('manifest', {})
        if manifest:
            print(f"Package: {manifest.get('package', 'unknown')}")
            print(f"Version: {manifest.get('version_name', 'unknown')}")
            print(f"Разрешений: {len(manifest.get('permissions', []))}")
        
        identifiers = result_dict.get('identifiers', {})
        found = sum(1 for data in identifiers.values() if data.get('found'))
        total = len(identifiers)
        print(f"Идентификаторов найдено: {found}/{total}")
        print(f"Секретов найдено: {len(result_dict.get('secrets', []))}")
        print(f"Библиотек: {len(result_dict.get('libraries', []))}")
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
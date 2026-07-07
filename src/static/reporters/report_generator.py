import json
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import markdown

from src.models.analysis import AnalysisResult, RiskLevel


class ReportGenerator:
    """Генерация отчётов в различных форматах"""

    @staticmethod
    def generate_markdown(result: AnalysisResult) -> str:
        """Генерирует Markdown отчёт"""
        lines = []

        # Заголовок
        lines.append(f"# Анализ APK: {result.apk_file}\n")
        lines.append(f"**Дата анализа:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("---\n")

        # Информация о приложении
        if result.manifest:
            lines.append("## Информация о приложении\n")
            lines.append(f"- **Package:** `{result.manifest.package}`")
            lines.append(f"- **Version:** `{result.manifest.version_name}` ({result.manifest.version_code})")
            lines.append(f"- **Target SDK:** `{result.manifest.target_sdk}`")
            lines.append(f"- **Min SDK:** `{result.manifest.min_sdk}`\n")

            # Разрешения
            lines.append("## Разрешения (Permissions)\n")
            if result.manifest.permissions:
                dangerous = [p for p in result.manifest.permissions if p.is_dangerous]
                safe = [p for p in result.manifest.permissions if not p.is_dangerous]

                lines.append(f"**Всего разрешений:** {len(result.manifest.permissions)}")
                lines.append(f"**Опасных:** {len(dangerous)}")
                lines.append(f"**Безопасных:** {len(safe)}\n")

                if dangerous:
                    lines.append("### Опасные разрешения\n")
                    for p in dangerous:
                        desc = f" - {p.description}" if p.description else ""
                        lines.append(f"- `{p.name}`{desc}")

                lines.append("\n### Все разрешения\n")
                for p in result.manifest.permissions:
                    danger = "⚠️" if p.is_dangerous else "✅"
                    lines.append(f"- {danger} `{p.name}`")
            else:
                lines.append("Разрешения не найдены\n")

        # Идентификаторы
        lines.append("\n## Использование идентификаторов устройства\n")
        if result.identifiers:
            for name, ident in result.identifiers.items():
                if ident.found:
                    lines.append(f"\n### ✅ {name} **найден**")
                    if ident.risk_level:
                        lines.append(f"**Уровень риска:** `{ident.risk_level.value}`")
                    lines.append("\n**Найден в:**")
                    for loc in ident.locations[:5]:  # Показываем первые 5
                        lines.append(f"- `{loc['file']}` (строка {loc['line']})")
                        if loc.get('code'):
                            lines.append(f"  ```java\n  {loc['code']}\n  ```")
                else:
                    lines.append(f"\n### ❌ {name} **не найден**")
        else:
            lines.append("Идентификаторы не анализировались\n")

        # Секреты
        lines.append("\n## Секреты и чувствительные данные\n")
        if result.secrets:
            lines.append(f"**Найдено секретов:** {len(result.secrets)}\n")
            for secret in result.secrets:
                lines.append(f"- **{secret.type}:** `{secret.value}`")
                lines.append(f"  - **Местоположение:** `{secret.location}`")
                lines.append(f"  - **Риск:** `{secret.risk_level.value}`\n")
        else:
            lines.append("Секреты не найдены ✅\n")

        # Библиотеки
        lines.append("\n## Используемые библиотеки\n")
        if result.libraries:
            for lib in sorted(result.libraries)[:20]:
                lines.append(f"- `{lib}`")
            if len(result.libraries) > 20:
                lines.append(f"\n*... и ещё {len(result.libraries) - 20} библиотек*")
        else:
            lines.append("Библиотеки не определены\n")

        # Резюме
        lines.append("\n## Резюме\n")
        if result.summary:
            lines.append(f"- **APK:** `{result.apk_file}`")
            if result.manifest:
                lines.append(f"- **Package:** `{result.manifest.package}`")
                lines.append(f"- **Version:** `{result.manifest.version_name}`")
            lines.append(f"- **Идентификаторы найдены:** {sum(1 for i in result.identifiers.values() if i.found)}/{len(result.identifiers)}")
            lines.append(f"- **Секреты найдены:** {len(result.secrets)}")
            lines.append(f"- **Библиотек обнаружено:** {len(result.libraries)}")

        return "\n".join(lines)

    @staticmethod
    def generate_json(result: AnalysisResult) -> str:
        """Генерирует JSON отчёт"""
        return json.dumps(result.model_dump(), indent=2, default=str, ensure_ascii=False)

    @staticmethod
    def generate_html(result: AnalysisResult) -> str:
        """Генерирует HTML отчёт"""
        md_content = ReportGenerator.generate_markdown(result)
        html_content = markdown.markdown(md_content, extensions=['extra', 'tables'])
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>APK Analysis Report - {result.apk_file}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 30px;
            background: #f8f9fa;
            color: #212529;
            line-height: 1.6;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            border: 1px solid #e9ecef;
        }}
        h1 {{
            color: #1a73e8;
            border-bottom: 2px solid #e8f0fe;
            padding-bottom: 15px;
            margin-top: 0;
        }}
        h2 {{
            color: #3c4043;
            border-bottom: 1px solid #e8eaed;
            padding-bottom: 8px;
            margin-top: 30px;
        }}
        h3 {{
            color: #137333;
            margin-top: 20px;
        }}
        code {{
            background: #f1f3f4;
            color: #c7254e;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 14px;
            font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
        }}
        pre {{
            background: #202124;
            color: #f1f3f4;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
        }}
        pre code {{
            background: transparent;
            color: inherit;
            padding: 0;
            font-size: 13px;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 6px;
        }}
        hr {{
            border: 0;
            border-top: 1px solid #e8eaed;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>
"""

    @staticmethod
    def save_report(result: AnalysisResult, output_dir: Path, formats: list = ["md", "json", "html"]):
        """Сохраняет отчёт в указанные форматы"""
        output_dir.mkdir(exist_ok=True, parents=True)
        stem = Path(result.apk_file).stem

        if "md" in formats:
            md_path = output_dir / f"{stem}_report.md"
            md_path.write_text(ReportGenerator.generate_markdown(result), encoding='utf-8')

        if "json" in formats:
            json_path = output_dir / f"{stem}_report.json"
            json_path.write_text(ReportGenerator.generate_json(result), encoding='utf-8')

        if "html" in formats:
            html_path = output_dir / f"{stem}_report.html"
            html_path.write_text(ReportGenerator.generate_html(result), encoding='utf-8')
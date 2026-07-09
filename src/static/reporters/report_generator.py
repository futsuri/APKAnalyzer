import json
from pathlib import Path
from datetime import datetime

import markdown

from src.models.analysis import AnalysisResult


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
            for finding in result.identifiers.values():
                title = f"{finding.identifier_id} — {finding.name}"
                if finding.found:
                    lines.append(f"\n### ✅ {title} **найден**")
                    lines.append(f"**Категория:** `{finding.category}`")
                    lines.append(f"**Критичность:** `{finding.severity}`")
                    lines.append(
                        f"**Сигнал:** {'strong (permission + signature)' if finding.permissions_present_in_manifest else 'signature-only'}"
                    )
                    if finding.permissions:
                        lines.append(
                            f"**Permissions:** `{', '.join(finding.permissions)}`"
                        )
                    if finding.matched_signature:
                        lines.append(f"**Matched signature:** `{finding.matched_signature}`")

                    app_occurrences = [occ for occ in finding.occurrences if not occ.is_third_party]
                    third_party_occurrences = [occ for occ in finding.occurrences if occ.is_third_party]
                    lines.append(
                        f"**Вхождений:** app={len(app_occurrences)}, sdk={len(third_party_occurrences)}"
                    )

                    lines.append("\n**Найден в:**")
                    for occurrence in finding.occurrences[:5]:
                        source_tag = "SDK" if occurrence.is_third_party else "APP"
                        lines.append(
                            f"- [{source_tag}] `{occurrence.file}` (строка {occurrence.line})"
                        )
                        if occurrence.code:
                            lines.append(f"  ```text\n  {occurrence.code}\n  ```")
                else:
                    lines.append(f"\n### ❌ {title} **не найден**")
                    lines.append(f"**Категория:** `{finding.category}`")
                    lines.append(f"**Критичность:** `{finding.severity}`")
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
            lines.append(
                f"- **Strong signals:** {sum(1 for i in result.identifiers.values() if i.found and i.permissions_present_in_manifest)}"
            )
            lines.append(f"- **Секреты найдены:** {len(result.secrets)}")
            lines.append(f"- **Библиотек обнаружено:** {len(result.libraries)}")

        return "\n".join(lines)

    @staticmethod
    def generate_json(result: AnalysisResult) -> str:
        """Генерирует JSON отчёт"""
        return json.dumps(result.model_dump(), indent=2, default=str)

    @staticmethod
    def generate_html(result: AnalysisResult) -> str:
        """Генерирует HTML отчёт"""
        md_content = ReportGenerator.generate_markdown(result)
        html_content = markdown.markdown(md_content, extensions=['extra', 'tables'])
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>APK Analysis Report</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 14px; }}
                pre {{ background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 6px; overflow-x: auto; }}
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
        output_dir.mkdir(parents=True, exist_ok=True)
        report_name = Path(result.apk_file).stem

        if "md" in formats:
            md_path = output_dir / f"{report_name}_report.md"
            md_path.write_text(ReportGenerator.generate_markdown(result), encoding='utf-8')

        if "json" in formats:
            json_path = output_dir / f"{report_name}_report.json"
            json_path.write_text(ReportGenerator.generate_json(result), encoding='utf-8')

        if "html" in formats:
            html_path = output_dir / f"{report_name}_report.html"
            html_path.write_text(ReportGenerator.generate_html(result), encoding='utf-8')
# APK Analyzer

CLI-инструмент для статического анализа Android APK.

## Быстрый запуск через Docker (рекомендуется)

### Windows

```bat
run_analyzer.bat path\to\app.apk
```

### Linux/macOS

```bash
chmod +x run_analyzer.sh
./run_analyzer.sh /path/to/app.apk
```

Скрипты автоматически:
1. Собирают Docker-образ `apk-analyzer`.
2. Монтируют `./data` в контейнер для сохранения отчётов.
3. Монтируют папку с APK в `/app/input`.
4. Запускают анализ.

Отчёты создаются в `data/output/static/` в форматах:
- Markdown (`*_report.md`)
- JSON (`*_report.json`)
- HTML (`*_report.html`)

## Ручной запуск в контейнере

```bash
docker build -t apk-analyzer .
docker run --rm -v "$(pwd)/data:/app/data" -v "/path/to/apk/folder:/app/input:ro" apk-analyzer "/app/input/app.apk"
```

## Проверка конфигурации

```bash
python test_config.py
```

`test_config.py` корректно обрабатывает и абсолютные пути, и имена команд (`apktool`, `jadx`, `java`) через PATH.

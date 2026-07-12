# APK Analyzer (Docker)

CLI-инструмент для статического и динамического анализа Android APK.

## Архитектура (Docker)

Три независимых сервиса (`docker-compose.yml`):

| Сервис | Dockerfile | Назначение |
|--------|------------|------------|
| `apk-analyzer-static` | `Dockerfile.static` | Статика: apktool + jadx + java |
| `apk-analyzer-dynamic` | `Dockerfile.dynamic` | Динамика: adb + frida-tools (без Java) |
| `android-emulator` | `docker/.../android-emulator/Dockerfile` | Эмулятор + frida-server |

Сервисы независимы: падение `dynamic` (или эмулятора) **не роняет** `static`.
`apk-analyzer-dynamic` имеет `restart: on-failure:3` (без бесконечного лупа).

## Быстрый запуск через Docker

### Статический анализ

#### Windows

```bat
run_analyzer.bat path\to\app.apk
```

#### Linux/macOS

```bash
chmod +x run_analyzer.sh
./run_analyzer.sh /path/to/app.apk
```

### Динамический анализ

```bash
# Через скрипт (соберёт apk-analyzer-dynamic образ)
./run_analyzer.sh /path/to/app.apk --mode dynamic --package com.example.app

# Или полный стек через compose
docker compose up -d android-emulator
docker compose run --rm apk-analyzer-dynamic \
    /app/input/app.apk --mode dynamic --package com.example.app
```

Скрипты автоматически:
1. Собирают нужный Docker-образ (`apk-analyzer-static` или `apk-analyzer-dynamic`).
2. Монтируют `./data` в контейнер для сохранения отчётов.
3. Монтируют папку с APK в `/app/input`.
4. Запускают анализ.

Отчёты создаются в `data/output/static/` и `data/output/dynamic/` в форматах:
- Markdown (`*_report.md`)
- JSON (`*_report.json`)
- HTML (`*_report.html`)

Немаскированные значения динамики (технический файл, не отчёт):
`data/output/dynamic/<apk>_raw_values.json`.

## Полный стек через docker compose

```bash
# Поднять эмулятор + статический анализатор (не зависят друг от друга)
docker compose up -d android-emulator apk-analyzer-static

# Динамический анализ на конкретном APK
docker compose run --rm apk-analyzer-dynamic \
    /app/input/app.apk --mode dynamic --package com.example.app
```

### Сеть и тома

- Общая сеть: `backend` (объявлена в эмуляторном compose).
- Общий том: `./data:/app/data` (отчёты + raw-значения).
- `EMULATOR_HOST=android-emulator` передаётся в dynamic-контейнер.

## Ручной запуск в контейнере

### Статика

```bash
docker build -t apk-analyzer-static -f Dockerfile.static .
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  -v "/path/to/apk/folder:/app/input:ro" \
  apk-analyzer-static "/app/input/app.apk"
```

### Динамика

```bash
docker build -t apk-analyzer-dynamic -f Dockerfile.dynamic .
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  -v "/path/to/apk/folder:/app/input:ro" \
  -e EMULATOR_HOST=android-emulator \
  --network backend \
  apk-analyzer-dynamic "/app/input/app.apk" --mode dynamic --package com.example.app
```

## Проверка конфигурации (статика)

```bash
python test_config.py
```

`test_config.py` корректно обрабатывает и абсолютные пути, и имена команд
(`apktool`, `jadx`, `java`) через PATH.

## Динамический анализ — e2e чек-лист

1. **Эмулятор**: `docker compose up -d android-emulator`.
2. **frida-server**: запущен в эмуляторе (`adb shell /data/local/tmp/frida-server &`).
   Образ эмулятора делает это автоматически в `entrypoint.sh`.
3. **Сеть**: анализатор и эмулятор в одной docker-сети `backend`.
4. **Версии frida**: клиентская библиотека (`frida==17.x`) совпадает по
   мажор-версии с `frida-server`.
5. **Запуск**: `main.py --mode dynamic --package <pkg> app.apk`.
6. **Результат**: отчёты в `data/output/dynamic/`, raw-значения в
   `<apk>_raw_values.json`.

# APK Analyzer

Статический + динамический анализатор Android APK.

> Выберите режим ниже (раскройте нужный блок):

<details open>
<summary><strong>Classic (ручная установка на хост)</strong></summary>

## Быстрый старт (Classic)

1. Установите Java 11+, Python 3.8+, Apktool 3.0.2, JADX 1.5.5.
2. Настройте пути в `.env` или `config.yaml`.
3. Установите Python-зависимости:

```bash
pip install -r requirements.txt
```

4. Проверьте конфигурацию:

```bash
python test_config.py
```

5. Запустите анализ:

```bash
# Статика (по умолчанию)
python main.py path/to/app.apk

# Динамика (нужен эмулятор с frida-server)
python main.py path/to/app.apk --mode dynamic --package com.example.app

# Оба режима
python main.py path/to/app.apk --mode full --package com.example.app
```

Отчёты: `data/output/static/` и `data/output/dynamic/` (`md`, `json`, `html`).

Полная версия: [README.classic.md](README.classic.md)

</details>

<details>
<summary><strong>Docker (без установки зависимостей на хост)</strong></summary>

## Быстрый старт (Docker)

### Статический анализ

### Windows

```bat
run_analyzer.bat path\to\app.apk
```

### Linux/macOS

```bash
chmod +x run_analyzer.sh
./run_analyzer.sh /path/to/app.apk
```

### Динамический анализ

```bash
./run_analyzer.sh /path/to/app.apk --mode dynamic --package com.example.app
# или полный стек через docker compose (см. ниже)
```

### Полный стек через docker compose

```bash
# Поднять эмулятор + оба анализатора (независимые сервисы)
docker compose up -d android-emulator apk-analyzer-static

# Запустить динамический анализ на конкретном APK
docker compose run --rm apk-analyzer-dynamic \
    /app/input/app.apk --mode dynamic --package com.example.app
```

Скрипты автоматически:
1. Собирают нужный Docker-образ (`apk-analyzer-static` или `apk-analyzer-dynamic`).
2. Монтируют `./data` для отчётов.
3. Монтируют папку с APK в контейнер.
4. Запускают анализ.

Отчёты: `data/output/static/` и `data/output/dynamic/` (`md`, `json`, `html`).

Полная версия: [README.docker.md](README.docker.md)

</details>

## Режимы анализа (`--mode`)

| Режим | Что делает | Требования |
|-------|------------|------------|
| `static` (по умолчанию) | Декомпиляция, поиск идентификаторов/секретов | apktool, jadx, java |
| `dynamic` | Frida-хуки на эмуляторе, перехват значений | эмулятор + frida-server |
| `full` | Статика + динамика | всё из обоих |

Флаги для `dynamic`/`full`:
- `--package <name>` — имя пакета (обязателен)
- `--emulator-host <host>` — хост эмулятора (default: `EMULATOR_HOST` или `android-emulator`)

## Динамический анализ — e2e чек-лист

Реальный прогон на эмуляторе (вне тестов):

1. **Эмулятор**: поднять через `docker compose up -d android-emulator`.
2. **frida-server**: должен быть запущен в эмуляторе
   (`adb shell /data/local/tmp/frida-server &`). Образ эмулятора делает это
   автоматически в `entrypoint.sh`.
3. **Сеть**: анализатор и эмулятор в одной docker-сети `backend`.
   `EMULATOR_HOST=android-emulator` (имя сервиса).
4. **Версии frida**: клиентская библиотека (`frida==17.x`) должна совпадать по
   мажор-версии с `frida-server` в эмуляторе.
5. **Запуск**:
   ```bash
   python main.py app.apk --mode dynamic --package com.example.app \
       --emulator-host android-emulator
   ```
6. **Результат**: отчёты в `data/output/dynamic/` (значения замаскированы),
   немаскированные значения — в `<apk>_raw_values.json` (задел под сверку с
   трафик-модулем).

## Локальное переключение README (опционально)

Если нужно физически подменять `README.md` в репозитории:

- Windows: `switch_readme.bat classic` / `switch_readme.bat docker`
- Linux/macOS: `./switch_readme.sh classic` / `./switch_readme.sh docker`
- напрямую: `python scripts/switch_readme.py classic|docker`

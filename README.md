# APK Analyzer

Статический анализатор Android APK.

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
python main.py path/to/app.apk
```

Отчёты: `data/output/static/` (`md`, `json`, `html`).

Полная версия: [README.classic.md](README.classic.md)

</details>

<details>
<summary><strong>Docker (без установки зависимостей на хост)</strong></summary>

## Быстрый старт (Docker)

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
2. Монтируют `./data` для отчётов.
3. Монтируют папку с APK в контейнер.
4. Запускают анализ.

Отчёты: `data/output/static/` (`md`, `json`, `html`).

Полная версия: [README.docker.md](README.docker.md)

</details>

## Локальное переключение README (опционально)

Если нужно физически подменять `README.md` в репозитории:

- Windows: `switch_readme.bat classic` / `switch_readme.bat docker`
- Linux/macOS: `./switch_readme.sh classic` / `./switch_readme.sh docker`
- напрямую: `python scripts/switch_readme.py classic|docker`

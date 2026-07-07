# 📖 Руководство по установке и настройке APK Analyzer

## 📑 Содержание

1. [Установка Java](#-шаг-1-установка-java)
2. [Установка Python](#-шаг-2-установка-python)
3. [Установка инструментов](#️-шаг-3-установка-инструментов)
4. [Клонирование проекта](#-шаг-4-клонирование-проекта)
5. [Настройка проекта](#️-шаг-5-настройка-проекта)
6. [Установка зависимостей](#-шаг-6-установка-зависимостей-python)
7. [Проверка установки](#-шаг-7-проверка-установки)
8. [Запуск анализа](#-шаг-8-запуск-анализа)
9. [Частые проблемы](#-частые-проблемы)
10. [Необходимые файлы](#-список-необходимых-файлов)

---

# 🔧 Шаг 1. Установка Java

## 1.1 Проверка установленной версии

```bash
java -version
```

---

## 1.2 Если Java не установлена

Скачайте **Java 11** (или выше):

> https://adoptium.net/temurin/releases/?version=11

Выберите:

- Windows
- x64
- MSI Installer

Установите скачанный файл.

После установки снова выполните:

```bash
java -version
```

Ожидаемый результат:

```text
openjdk version "11.0.31" 2026-04-21
```

---

# 📦 Шаг 2. Установка Python

## 2.1 Проверка версии

```bash
python --version
```

Должно быть:

> Python **3.8** или выше.

---

## 2.2 Если Python не установлен

Скачайте Python:

> https://www.python.org/downloads/windows/

### ⚠️ Важно

Во время установки обязательно поставьте галочку:

✅ **Add Python to PATH**

---

# 🛠️ Шаг 3. Установка инструментов

## 3.1 Установка Apktool

Перейдите на сайт:

> https://apktool.org/

Скачайте два файла:

- `apktool_3.0.2.jar`
- `apktool.bat`

Положите оба файла в одну папку, например:

```text
C:\Users\Имя_пользователя\Downloads\
```

---

### ⚠️ Важно

Откройте `apktool.bat` в Блокноте и удалите последние две строки:

```bat
rem Pause when ran non interactively
for %%i in (%cmdcmdline%) do if /i "%%~i"=="/c" pause & exit /b
```

После удаления файл должен заканчиваться так:

```bat
"%java_exe%" -jar -Xmx1024M -Duser.language=en -Dfile.encoding=UTF8 -Djdk.util.zip.disableZip64ExtraFieldValidation=true -Djdk.nio.zipfs.allowDotZipEntry=true "%~dp0%BASENAME%%max%.jar" %fastCommand% %*
```

### Почему это нужно?

Эти строки заставляют `apktool` ждать нажатия клавиши после завершения работы.

При автоматическом анализе это приводит к зависанию программы.

---

### Проверка Apktool

```bash
cd C:\Users\Имя_пользователя\Downloads\
apktool.bat --version
```

Ожидаемый результат:

```text
3.0.2
```

---

## 3.2 Установка JADX

Страница релизов:

> https://github.com/skylot/jadx/releases

Скачайте:

```
jadx-1.5.5.zip
```

> ⚠️ Не скачивайте `jadx-gui-1.5.5-win.zip`.

Распакуйте архив:

```text
C:\Users\Имя_пользователя\Downloads\jadx-1.5.5\
```

Проверка:

```bash
cd C:\Users\Имя_пользователя\Downloads\jadx-1.5.5\bin
jadx.bat --version
```

---

# 📂 Шаг 4. Клонирование проекта

## Вариант 1. Git

```bash
git clone https://github.com/ваш-репозиторий/apk-analyzer.git
cd apk-analyzer
```

---

## Вариант 2. ZIP

1. Скачайте архив проекта.
2. Распакуйте его, например:

```text
C:\Users\Имя_пользователя\Downloads\apk-analyzer\
```

---

# ⚙️ Шаг 5. Настройка проекта

## 5.1 Создание `.env`

Создайте файл `.env` в корне проекта.

```env
APKTOOL_PATH=C:/Users/Имя_пользователя/Downloads/apktool.bat
JADX_PATH=C:/Users/Имя_пользователя/Downloads/jadx-1.5.5/bin/jadx.bat
JAVA_PATH=C:/Program Files/Eclipse Adoptium/jdk-11.0.31.11-hotspot/bin/java.exe
```

> ⚠️ Замените `Имя_пользователя` на своё имя пользователя Windows.

---

## 5.2 Проверка `config.yaml`

```yaml
tools:
  apktool: "C:/Users/Имя_пользователя/Downloads/apktool.bat"
  jadx: "C:/Users/Имя_пользователя/Downloads/jadx-1.5.5/bin/jadx.bat"
  java: "C:/Program Files/Eclipse Adoptium/jdk-11.0.31.11-hotspot/bin/java.exe"

analysis:
  timeout: 600
  max_libraries: 50
```

---

# 📦 Шаг 6. Установка зависимостей Python

Установите все зависимости:

```bash
pip install -r requirements.txt
```

Или минимальный набор:

```bash
pip install androguard markdown pyyaml python-dotenv
```

---

# ✅ Шаг 7. Проверка установки

## 7.1 Проверка конфигурации

```bash
python test_config.py
```

Ожидаемый результат:

```text
==================================================
ПРОВЕРКА КОНФИГУРАЦИИ
==================================================

APKTOOL_PATH: C:/Users/...
JADX_PATH:    C:/Users/...
JAVA_PATH:    C:/Program Files/...

TIMEOUT:      600

ПРОВЕРКА СУЩЕСТВОВАНИЯ ФАЙЛОВ:

apktool: True
jadx:    True
java:    True
```

Все значения должны быть **True**.

---

## 7.2 Проверка Apktool

```bash
cd C:\Users\Имя_пользователя\Downloads\
apktool.bat d Signal-8.17.4.apk -o test_apktool -f
```

Если программа завершилась **без ожидания нажатия клавиши**, всё настроено правильно.

---

# 🚀 Шаг 8. Запуск анализа

## 8.1 Скопируйте APK

```bash
copy C:\путь\к\вашему\app.apk .
```

---

## 8.2 Запуск

```bash
python main.py app.apk
```

---

## 8.3 Результат

После завершения анализа появится примерно такой вывод:

```text
============================================================
РЕЗУЛЬТАТЫ АНАЛИЗА
============================================================

APK: app.apk
Package: org.example.app
Version: 1.0.0

Разрешений: 25
Идентификаторов найдено: 5/8
Секретов найдено: 12
Библиотек: 15

============================================================
```

---

## 8.4 Где находятся отчёты

```text
data/output/static/
├── app_report.md
└── app_report.json
```

---

# 🐛 Частые проблемы

## ❌ Apktool зависает

### Причина

В файле `apktool.bat` остались строки:

```bat
rem Pause when ran non interactively
for %%i in (%cmdcmdline%) do if /i "%%~i"=="/c" pause & exit /b
```

### Решение

Удалите их.

---

## ❌ Java 8 вместо Java 11

### Решение

- Установите Java 11.
- Поднимите Java 11 выше Java 8 в переменной PATH.
- Перезапустите терминал.

---

## ❌ ModuleNotFoundError

```bash
pip install androguard markdown pyyaml python-dotenv
```

---

## ❌ Apktool не найден

Проверьте путь в `.env`.

```env
APKTOOL_PATH=C:/Users/Имя_пользователя/Downloads/apktool.bat
```

---

## ❌ UnsupportedClassVersionError в JADX

### Причина

Используется Java ниже версии 11.

### Решение

Установите Java 11 или выше.

---

# 🎯 Список необходимых файлов

| Файл | Скачать | Куда поместить |
|-------|----------|----------------|
| `apktool_3.0.2.jar` | https://apktool.org/ | `C:\Users\Имя\Downloads\` |
| `apktool.bat` | https://apktool.org/ | `C:\Users\Имя\Downloads\` *(удалить последние 2 строки)* |
| `jadx-1.5.5.zip` | https://github.com/skylot/jadx/releases | `C:\Users\Имя\Downloads\jadx-1.5.5\` |
| Java 11+ | https://adoptium.net/ | Установить в систему |
| Python 3.8+ | https://www.python.org/ | Установить в систему |

---

# ✅ После выполнения всех шагов

Вы сможете запускать анализ APK одной командой:

```bash
python main.py вашфайл.apk
```

Отчёты будут сохранены в:

```text
data/output/static/
```
=======
# APKAnalyzer
A program designed for analyzing APK files, developed by students during their industrial training at the [removed]. Includes statistical, dynamic, permissions and software behavior analysis
>>>>>>> 6734d0cb368404524dea967ed9252c1546233deb

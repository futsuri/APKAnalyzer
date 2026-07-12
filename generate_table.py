#!/usr/bin/env python3
"""
Генератор таблицы регрессии из JSON-отчета статического анализа
Сохраняет результат в файл Таблица_регрессии.md
В колонку "Статический модуль" записываются только найденные идентификаторы
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def load_json_report(json_path):
    """Загружает JSON-отчет"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_identifier_status(identifier_id, identifiers_data, permissions_list):
    """
    Определяет статус идентификатора по данным из отчета
    Возвращает True, если идентификатор найден
    """
    # Проверяем, есть ли идентификатор в секции identifiers
    if identifier_id in identifiers_data:
        return identifiers_data[identifier_id].get("found", False)
    
    # Проверяем, является ли идентификатор разрешением (и есть ли оно в манифесте)
    if any(p.get("name") == identifier_id for p in permissions_list):
        return True
    
    return False

def generate_regression_table(data):
    """Генерирует данные для таблицы регрессии"""
    
    # Сценарии с соответствующими идентификаторами (из вашей таблицы)
    scenarios = {
        "Первый запуск": {
            "action": "Установить и открыть приложение",
            "identifiers": ["hw_imei", "hw_serial", "sw_android_id", "sw_aaid"]
        },
        "Согласие на разрешения": {
            "action": "Дать согласие/не дать согласие",
            "identifiers": ["hw_imei", "hw_serial", "sw_android_id", "sw_aaid", 
                           "READ_PHONE_STATE", "READ_CONTACTS", "ACCESS_FINE_LOCATION"]
        },
        "Авторизация": {
            "action": "Ввести логин, пароль, номер телефона",
            "identifiers": ["hw_imei", "hw_phone_number", "sw_android_id", "sw_aaid", "sw_oaid"]
        },
        "Открытие вкладки \"Чаты\"": {
            "action": "Нажать на вкладку \"Чаты\"",
            "identifiers": ["sw_android_id"]
        },
        "Открытие вкладки \"Контакты\"": {
            "action": "Нажать на вкладку \"Контакты\"",
            "identifiers": ["READ_CONTACTS", "hw_phone_number", "hw_imsi", "hw_iccid"]
        },
        "Открытие настроек профиля": {
            "action": "Нажать на иконку профиля",
            "identifiers": ["hw_serial", "os_build_fingerprint", "net_wifi_mac", "net_bssid", "ACCESS_FINE_LOCATION"]
        },
        "Отправка фото": {
            "action": "Прикрепить и отправить фото",
            "identifiers": ["CAMERA", "READ_EXTERNAL_STORAGE", "net_wifi_mac"]
        },
        "Отправка голосового сообщения": {
            "action": "Записать и отправить голосовое сообщение",
            "identifiers": ["RECORD_AUDIO"]
        },
        "Фоновый режим": {
            "action": "Свернуть приложение, подождать 2-5 минут, открыть снова",
            "identifiers": ["sw_android_id", "sw_aaid"]
        },
        "Активность сети": {
            "action": "Выполнить действия, требующие сети",
            "identifiers": ["sw_android_id", "sw_gsf_id", "sw_aaid", "os_build_fingerprint", "drm_widevine_id", "sw_oaid"]
        },
        "Завершение работы": {
            "action": "Закрыть приложение",
            "identifiers": ["session_id", "user_id", "session.start", "session.stop"]
        }
    }
    
    # Получаем данные из отчета
    identifiers = data.get("identifiers", {})
    permissions = data.get("manifest", {}).get("permissions", [])
    
    # Формируем результаты для каждого сценария
    results = []
    for scenario, config in scenarios.items():
        row = {
            "scenario": scenario,
            "action": config["action"],
            "identifiers": config["identifiers"],
            "found_identifiers": [],  # Только те, что найдены
            "static_value": ""        # Строка для колонки "Статический модуль"
        }
        
        # Проверяем каждый идентификатор
        for identifier in config["identifiers"]:
            if get_identifier_status(identifier, identifiers, permissions):
                row["found_identifiers"].append(identifier)
        
        # Формируем строку для колонки "Статический модуль"
        if row["found_identifiers"]:
            row["static_value"] = ", ".join(row["found_identifiers"])
        else:
            row["static_value"] = "—"  # Если ничего не найдено
        
        results.append(row)
    
    return results

def generate_markdown_table(results, package_name, version, apk_file, analysis_date):
    """Генерирует Markdown-таблицу по вашему шаблону (без колонки "Что запрашивается")"""
    
    md = []
    
    # Заголовок
    md.append("")
    md.append(f"**Название приложения:** `{package_name}`")
    md.append(f"**Дата тестирования:** `{analysis_date}`")
    md.append(f"**Версия приложения:** `{version}`")
    md.append("")
    
    # 1. Общая информация
    md.append("## 1. Общая информация")
    md.append("")
    md.append("| Параметр | Значение |")
    md.append("| -------- | -------- |")
    md.append(f"| Package Name | `{package_name}` |")
    md.append(f"| Version | `{version}` |")
    md.append("")
    
    # 2. Таблица регрессии
    md.append("## 2. Результаты по сценариям")
    md.append("")
    md.append("| Сценарий | Действие пользователя | Связанные идентификаторы | Статический модуль | Динамический модуль | Трафик | Финал |")
    md.append("| -------- | --------------------- | ------------------------ | ------------------ | ------------------- | ------ | ----- |")
    
    for row in results:
        # Колонка "Связанные идентификаторы" — все идентификаторы сценария
        all_identifiers_str = "`, `".join(row["identifiers"])
        if all_identifiers_str:
            all_identifiers_str = f"`{all_identifiers_str}`"
        else:
            all_identifiers_str = ""
        
        md.append(f"| {row['scenario']} | {row['action']} | {all_identifiers_str} | {row['static_value']} |  |  |  |")
    
    md.append("")
    md.append("---")
    md.append("")
    md.append("*Таблица сгенерирована автоматически на основе JSON-отчета статического анализа.*")
    
    return "\n".join(md)

def save_markdown_file(md_content, json_path):
    """Сохраняет Markdown-файл рядом с JSON-отчетом"""
    output_path = json_path.parent / "Таблица_регрессии.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    return output_path

def main():
    if len(sys.argv) < 2:
        print("❌ Укажите путь к JSON-отчету")
        print(f"   python3 {sys.argv[0]} Signal-8.17.4_report.json")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"❌ Файл не найден: {json_path}")
        sys.exit(1)
    
    # Загружаем данные
    data = load_json_report(json_path)
    
    # Получаем информацию о приложении
    manifest = data.get("manifest", {})
    package = manifest.get("package", "unknown")
    version = manifest.get("version_name", "unknown")
    apk_file = data.get("apk_file", json_path.name)
    analysis_date = datetime.now().strftime("%Y-%m-%d")
    
    # Генерируем таблицу
    results = generate_regression_table(data)
    
    # Генерируем Markdown
    md_content = generate_markdown_table(results, package, version, apk_file, analysis_date)
    
    # Сохраняем в файл
    output_path = save_markdown_file(md_content, json_path)
    
    # Статистика
    total_scenarios = len(results)
    scenarios_with_found = sum(1 for row in results if row["found_identifiers"])
    
    print(f"✅ Таблица регрессии сохранена: {output_path}")
    print(f"\n📊 Сценариев с найденными идентификаторами: {scenarios_with_found} из {total_scenarios}")
    
    # Показываем, что найдено в каждом сценарии
    print("\n🔍 Найденные идентификаторы по сценариям:")
    for row in results:
        if row["found_identifiers"]:
            print(f"   {row['scenario']}: {', '.join(row['found_identifiers'])}")
        else:
            print(f"   {row['scenario']}: ❌ ничего не найдено")

if __name__ == "__main__":
    main()

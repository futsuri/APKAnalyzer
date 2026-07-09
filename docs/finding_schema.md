# Finding schema

Статический модуль возвращает находки идентификаторов в `AnalysisResult.identifiers`
как словарь `{identifier_id: Finding}`.

## JSON-форма Finding

```json
{
  "identifier_id": "hw_imei",
  "name": "IMEI / International Mobile Equipment Identity",
  "category": "hardware",
  "severity": "CRITICAL",
  "description": "Международный идентификатор мобильного оборудования.",
  "permissions": [
    "android.permission.READ_PHONE_STATE"
  ],
  "found": true,
  "matched_signature": "Landroid/telephony/TelephonyManager;->getDeviceId",
  "occurrences": [
    {
      "file": "smali/com/example/app/MainActivity.smali",
      "line": 42,
      "code": "invoke-virtual {v0}, Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;",
      "is_third_party": false,
      "package_guess": "com.example.app"
    }
  ],
  "permissions_present_in_manifest": true,
  "frida_hook": {
    "class": "android.telephony.TelephonyManager",
    "methods": ["getDeviceId", "getImei"]
  },
  "traffic_detection": {
    "transformations": ["plain", "sha256"],
    "evidence_target": "traffic.evidence"
  }
}
```

## Поля

- `identifier_id` — ID записи из `identifiers_catalog.yaml`.
- `name` — человекочитаемое имя идентификатора.
- `category` — категория (`hardware`, `software`, `network`, ...).
- `severity` — критичность из каталога.
- `description` — описание из каталога.
- `permissions` — ожидаемые разрешения из каталога.
- `found` — найдена ли сигнатура в коде.
- `matched_signature` — первая совпавшая сигнатура.
- `occurrences` — все найденные вхождения.
  - `file` — путь файла в артефактах декомпиляции.
  - `line` — номер строки.
  - `code` — фрагмент исходной строки.
  - `is_third_party` — эвристика принадлежности к стороннему SDK.
  - `package_guess` — предполагаемый package по пути файла.
- `permissions_present_in_manifest` — все ли `permissions` из каталога
  присутствуют в `AndroidManifest.xml`.
- `frida_hook` — метаданные для динамического модуля.
- `traffic_detection` — метаданные для модуля анализа трафика.

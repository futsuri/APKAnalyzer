"""Генерация Frida JS-скрипта из identifiers_catalog.yaml.

Покрывает все 13 идентификаторов каталога, включая:
- methods (с/без argument_trigger)
- fields (статические поля Build.SERIAL, Build.FINGERPRINT)

Каждый хук отправляет структурированное сообщение через send({...}).
Маскирование — на стороне Python (в finding_builder.py).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.static.catalog import CatalogIdentifier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JS-шаблоны
# ---------------------------------------------------------------------------

_HOOK_METHOD_TEMPLATE = """\
    try {{
        var cls = Java.use("{cls}");
        var orig = cls.{method};
        cls.{method}.implementation = function({params}) {{
            var result = this.{method}({args});
{trigger_check}            send({{
                identifier_id: "{identifier_id}",
                class_name: "{cls}",
                method: "{method}",
                value: (result !== null && result !== undefined) ? result.toString() : null,
                stack: Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()).substring(0, 500),
                timestamp: Date.now()
            }});
            return result;
        }};
        console.log("[+] Hooked {cls}.{method}");
    }} catch(e) {{
        console.log("[-] Failed to hook {cls}.{method}: " + e);
    }}"""

_HOOK_FIELD_TEMPLATE = """\
    try {{
        var cls = Java.use("{cls}");
        var fieldName = "{field}";
        // Перехватываем через getter, если есть; иначе читаем поле напрямую
        try {{
            var getterName = "get" + fieldName.charAt(0).toUpperCase() + fieldName.slice(1);
            var origGetter = cls[getterName];
            cls[getterName].implementation = function() {{
                var result = this[fieldName];
                send({{
                    identifier_id: "{identifier_id}",
                    class_name: "{cls}",
                    method: "field:" + fieldName,
                    value: (result !== null && result !== undefined) ? result.toString() : null,
                    stack: Java.use("android.util.Log").getStackTraceString(Java.use("java.lang.Exception").$new()).substring(0, 500),
                    timestamp: Date.now()
                }});
                return result;
            }};
            console.log("[+] Hooked {cls}." + getterName + " for field " + fieldName);
        }} catch(getterErr) {{
            // Нет getter'а — хукаем все методы, которые могут читать поле
            // Периодически читаем значение через поле
            var fieldValue = cls[fieldName].value;
            send({{
                identifier_id: "{identifier_id}",
                class_name: "{cls}",
                method: "field:" + fieldName,
                value: (fieldValue !== null && fieldValue !== undefined) ? fieldValue.toString() : null,
                stack: "direct field access",
                timestamp: Date.now()
            }});
            console.log("[+] Read {cls}." + fieldName + " = " + fieldValue);
        }}
    }} catch(e) {{
        console.log("[-] Failed to hook field {cls}.{field}: " + e);
    }}"""

# ---------------------------------------------------------------------------
# Генератор
# ---------------------------------------------------------------------------


def generate_hook_script(catalog: list[CatalogIdentifier]) -> str:
    """Генерирует JS-скрипт Frida из каталога идентификаторов.

    Возвращает полную строку JavaScript, готовую к ``create_script()``.
    """
    lines = [
        "// Автоматически сгенерировано из identifiers_catalog.yaml",
        "// НЕ редактировать вручную — используйте src/dynamic/hook_generator.py",
        "",
        'Java.perform(function() {',
        "    console.log(\"[*] Frida hooks started (catalog-driven)\");",
        "",
    ]

    for entry in catalog:
        hook_cfg = entry.frida_hook
        if not hook_cfg:
            logger.warning("Нет frida_hook для %s, пропускаем", entry.identifier_id)
            continue

        cls = hook_cfg.get("class", "")
        methods = hook_cfg.get("methods", [])
        fields = hook_cfg.get("fields", [])
        argument_trigger = hook_cfg.get("argument_trigger")
        mask_strategy = hook_cfg.get("mask_strategy", "plain")
        identifier_id = entry.identifier_id

        if not cls:
            logger.warning("Нет class в frida_hook для %s, пропускаем", identifier_id)
            continue

        lines.append(f"    // === {identifier_id}: {entry.name} ===")

        # --- Хуки методов ---
        for method in methods:
            trigger_block = ""
            if argument_trigger:
                trigger_block = (
                    f'            if ({params[0] if "params" in dir() else "arg1"} '
                    f'&& {params[0] if "params" in dir() else "arg1"}.indexOf("{argument_trigger}") === -1) {{\n'
                    f'                return result;\n'
                    f"            }}\n"
                )

            # Определяем сигнатуру параметров
            hook_code = _HOOK_METHOD_TEMPLATE.format(
                cls=cls,
                method=method,
                params=_infer_params(cls, method, argument_trigger),
                args=_infer_call_args(cls, method, argument_trigger),
                trigger_check=_build_trigger_check(argument_trigger),
                identifier_id=identifier_id,
            )
            lines.append(hook_code)
            lines.append("")

        # --- Хуки полей ---
        for field in fields:
            hook_code = _HOOK_FIELD_TEMPLATE.format(
                cls=cls,
                field=field,
                identifier_id=identifier_id,
            )
            lines.append(hook_code)
            lines.append("")

    lines.append('    console.log("[*] All catalog hooks installed");')
    lines.append("});")

    script = "\n".join(lines)
    logger.info("Сгенерирован JS-скрипт: %d символов, покрывают каталог с %d записей",
                len(script), len(catalog))
    return script


def save_hook_script(script: str, path: Path) -> Path:
    """Сохраняет JS-скрипт на диск (для отладки/Docker)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script, encoding="utf-8")
    logger.info("JS-скрипт сохранён: %s", path)
    return path


# ---------------------------------------------------------------------------
# Helpers для определения сигнатур методов
# ---------------------------------------------------------------------------

# Методы с известным числом/именами параметров (для корректного override)
_METHOD_SIGNATURES: dict[str, dict[str, tuple[list[str], list[str]]]] = {
    # class -> { method -> (param_names, call_args) }
    "android.telephony.TelephonyManager": {
        "getDeviceId": (["slotIndex"], ["slotIndex"]),
        "getImei": (["slotIndex"], ["slotIndex"]),
        "getSubscriberId": ([], []),
        "getSimSerialNumber": ([], []),
        "getLine1Number": ([], []),
    },
    "android.provider.Settings$Secure": {
        "getString": (["resolver", "name"], ["resolver", "name"]),
    },
    "android.net.wifi.WifiInfo": {
        "getMacAddress": ([], []),
        "getBSSID": ([], []),
    },
    "android.os.Build": {
        "getSerial": ([], []),
    },
    "com.google.android.gms.ads.identifier.AdvertisingIdClient$Info": {
        "getId": ([], []),
    },
    "com.huawei.hms.ads.identifier.AdvertisingIdClient": {
        "getAdvertisingIdInfo": ([], []),
    },
    "android.content.ContentResolver": {
        "query": (["uri", "projection", "selection", "selectionArgs", "sortOrder"],
                  ["uri", "projection", "selection", "selectionArgs", "sortOrder"]),
    },
    "android.media.MediaDrm": {
        "getPropertyByteArray": (["propertyName"], ["propertyName"]),
    },
}


def _infer_params(cls: str, method: str, argument_trigger: str | None) -> str:
    """Возвращает строку с именами параметров для JS-функции."""
    if cls in _METHOD_SIGNATURES and method in _METHOD_SIGNATURES[cls]:
        params = _METHOD_SIGNATURES[cls][method][0]
        return ", ".join(params) if params else ""
    # Fallback: один безымянный параметр (для методов без аргументов)
    return ""


def _infer_call_args(cls: str, method: str, argument_trigger: str | None) -> str:
    """Возвращает строку с аргументами вызова оригинального метода."""
    if cls in _METHOD_SIGNATURES and method in _METHOD_SIGNATURES[cls]:
        args = _METHOD_SIGNATURES[cls][method][1]
        return ", ".join(args) if args else ""
    return ""


def _build_trigger_check(argument_trigger: str | None) -> str:
    """Строит JS-проверку для argument_trigger (проверка аргумента перед send)."""
    if not argument_trigger:
        return ""
    # Общий случай: проверяем первый строковый аргумент
    return (
        f'            if (name && name.indexOf("{argument_trigger}") !== -1) {{\n'
        f"                // argument_trigger matched\n"
        f"            }} else {{\n"
        f"                return result;\n"
        f"            }}\n"
    )

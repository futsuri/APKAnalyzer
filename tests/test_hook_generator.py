"""Тесты генерации Frida-хуков из identifiers_catalog.yaml.

Проверяет, что все 13 идентификаторов каталога покрываются,
JS содержит send({...}) с identifier_id, методы и поля обрабатываются.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.static.catalog import load_identifiers_catalog, CatalogIdentifier
from src.dynamic.hook_generator import generate_hook_script

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CATALOG_PATH = Path(__file__).resolve().parents[1] / "identifiers_catalog.yaml"


def _catalog() -> list[CatalogIdentifier]:
    return load_identifiers_catalog(CATALOG_PATH)


# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------

def test_generated_script_is_valid_js():
    """Сгенерированный скрипт начинается и заканчивается корректно."""
    catalog = _catalog()
    script = generate_hook_script(catalog)
    assert "Java.perform" in script
    assert "All catalog hooks installed" in script
    assert "Frida hooks started (catalog-driven)" in script


@pytest.mark.parametrize("entry", _catalog(), ids=lambda e: e.identifier_id)
def test_all_catalog_entries_have_send(entry: CatalogIdentifier):
    """Каждый идентификатор каталога генерирует хотя бы один send({...})."""
    catalog = _catalog()
    script = generate_hook_script(catalog)

    if not entry.frida_hook:
        pytest.skip(f"{entry.identifier_id}: нет frida_hook в каталоге")

    identifier_id = entry.identifier_id
    assert f'"{identifier_id}"' in script, (
        f"identifier_id '{identifier_id}' не найден в сгенерированном JS"
    )
    assert "send(" in script, "Нет вызова send()"


@pytest.mark.parametrize("entry", _catalog(), ids=lambda e: e.identifier_id)
def test_hook_covers_methods(entry: CatalogIdentifier):
    """Для каждого метода из frida_hook.methods есть хук с implementation."""
    if not entry.frida_hook or not entry.frida_hook.get("methods"):
        pytest.skip(f"{entry.identifier_id}: нет methods")

    catalog = _catalog()
    script = generate_hook_script(catalog)
    cls = entry.frida_hook["class"]
    identifier_id = entry.identifier_id

    for method in entry.frida_hook["methods"]:
        assert f"cls.{method}.implementation" in script, (
            f"{identifier_id}: нет .implementation для {cls}.{method}"
        )


@pytest.mark.parametrize("entry", _catalog(), ids=lambda e: e.identifier_id)
def test_hook_covers_fields(entry: CatalogIdentifier):
    """Для каждого поля из frida_hook.fields есть перехват."""
    if not entry.frida_hook or not entry.frida_hook.get("fields"):
        pytest.skip(f"{entry.identifier_id}: нет fields")

    catalog = _catalog()
    script = generate_hook_script(catalog)
    identifier_id = entry.identifier_id

    for field_name in entry.frida_hook["fields"]:
        assert field_name in script, (
            f"{identifier_id}: поле {field_name} не найдено в JS"
        )


def test_argument_trigger_generates_check():
    """identifier с argument_trigger содержит проверку indexOf."""
    catalog = _catalog()
    script = generate_hook_script(catalog)

    # sw_android_id имеет argument_trigger "android_id"
    assert '"android_id"' in script
    assert "indexOf" in script


def test_exact_13_identifiers_covered():
    """Все 13 идентификаторов каталога присутствуют в JS."""
    catalog = _catalog()
    script = generate_hook_script(catalog)
    assert len(catalog) == 13

    for entry in catalog:
        if entry.frida_hook:
            assert f'"{entry.identifier_id}"' in script, (
                f"{entry.identifier_id} не найден в JS"
            )


def test_no_console_log_hacks():
    """Нет старых console.log("[IMEI]" ...) — только send({...})."""
    catalog = _catalog()
    script = generate_hook_script(catalog)
    # Старый формат: console.log("[IMEI] " + result);
    assert 'console.log("[IMEI]"' not in script
    assert 'console.log("[MAC]"' not in script
    assert 'console.log("[ANDROID_ID]"' not in script


def test_structured_message_format():
    """send({...}) содержит обязательные поля: identifier_id, class_name, method, value."""
    catalog = _catalog()
    script = generate_hook_script(catalog)
    assert "identifier_id:" in script
    assert "class_name:" in script
    assert "method:" in script
    assert "value:" in script
    assert "stack:" in script
    assert "timestamp:" in script

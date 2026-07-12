"""Тесты сборки Finding из сырых Frida-сообщений.

Моки, без реального устройства. Проверяет:
- Finding создаётся для каждого identifier_id
- found = True при наличии сообщений
- маскирование применено
- сырое значение не в Finding (только masked)
- traffic_detection пустой
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.static.catalog import load_identifiers_catalog, CatalogIdentifier
from src.dynamic.finding_builder import build_findings, collect_raw_values


CATALOG_PATH = Path(__file__).resolve().parents[1] / "identifiers_catalog.yaml"


def _catalog() -> list[CatalogIdentifier]:
    return load_identifiers_catalog(CATALOG_PATH)


def _make_message(identifier_id: str, value: str, method: str = "test") -> dict:
    return {
        "identifier_id": identifier_id,
        "class_name": "com.example.Test",
        "method": method,
        "value": value,
        "stack": "at com.example.Test.run(Test.java:42)",
        "timestamp": 1700000000000,
    }


class TestBuildFindings:
    def test_all_catalog_entries_present(self):
        """Результат содержит все identifier_id из каталога."""
        catalog = _catalog()
        findings = build_findings([], catalog)
        assert set(findings.keys()) == {c.identifier_id for c in catalog}

    def test_found_true_when_message_exists(self):
        """found = True когда есть ≥1 сообщение с identifier_id."""
        catalog = _catalog()
        msg = _make_message("hw_imei", "123456789012345")
        findings = build_findings([msg], catalog)
        assert findings["hw_imei"].found is True

    def test_found_false_when_no_messages(self):
        """found = False когда нет сообщений."""
        catalog = _catalog()
        findings = build_findings([], catalog)
        assert all(not f.found for f in findings.values())

    def test_occurrences_contain_masked_values(self):
        """Значения в occurrences замаскированы."""
        catalog = _catalog()
        msg = _make_message("hw_imei", "123456789012345")
        findings = build_findings([msg], catalog)

        occ = findings["hw_imei"].occurrences[0]
        # hw_imei mask_strategy = sha256
        assert "123456789012345" not in occ.code
        assert len(occ.code) > 0  # замаскированное значение есть

    def test_traffic_detection_is_empty_dict(self):
        """traffic_detection всегда пустой {} — задел под СПМ-2."""
        catalog = _catalog()
        msg = _make_message("hw_imei", "123456789012345")
        findings = build_findings([msg], catalog)
        assert findings["hw_imei"].traffic_detection == {}

    def test_frida_hook_copied_from_catalog(self):
        """frida_hook копируется из каталога."""
        catalog = _catalog()
        findings = build_findings([], catalog)
        for entry in catalog:
            finding = findings[entry.identifier_id]
            if entry.frida_hook:
                assert finding.frida_hook == entry.frida_hook

    def test_null_undefined_values_ignored(self):
        """Сообщения с value = null/undefined не создают occurrence."""
        catalog = _catalog()
        msg = _make_message("hw_imei", "null")
        findings = build_findings([msg], catalog)
        assert not findings["hw_imei"].found

    def test_duplicate_values_deduped(self):
        """Одинаковые значения не дублируются в occurrences."""
        catalog = _catalog()
        msgs = [
            _make_message("hw_imei", "123456789012345"),
            _make_message("hw_imei", "123456789012345"),  # дубликат
        ]
        findings = build_findings(msgs, catalog)
        assert len(findings["hw_imei"].occurrences) == 1

    def test_different_values_not_deduped(self):
        """Разные значения создают отдельные occurrences."""
        catalog = _catalog()
        msgs = [
            _make_message("hw_imei", "111111111111111"),
            _make_message("hw_imei", "222222222222222"),
        ]
        findings = build_findings(msgs, catalog)
        assert len(findings["hw_imei"].occurrences) == 2

    def test_mac_address_masked_correctly(self):
        """net_wifi_mac маскируется через mac_anonymize."""
        catalog = _catalog()
        msg = _make_message("net_wifi_mac", "AA:BB:CC:DD:EE:FF")
        findings = build_findings([msg], catalog)
        occ = findings["net_wifi_mac"].occurrences[0]
        assert "AA:BB:00:00:EE:FF" in occ.code

    def test_phone_masked_correctly(self):
        """hw_phone_number маскируется через custom_phone_mask."""
        catalog = _catalog()
        msg = _make_message("hw_phone_number", "+79998887766")
        findings = build_findings([msg], catalog)
        occ = findings["hw_phone_number"].occurrences[0]
        # 11 цифр: 4 + 5 звёздочек + 2
        assert "+7999*****66" in occ.code


class TestCollectRawValues:
    def test_raw_values_unmasked(self):
        """collect_raw_values возвращает немаскированные значения."""
        msgs = [
            _make_message("hw_imei", "123456789012345"),
            _make_message("hw_imei", "987654321098765"),
        ]
        raw = collect_raw_values(msgs)
        assert raw["hw_imei"] == ["123456789012345", "987654321098765"]

    def test_raw_values_ignores_null(self):
        msgs = [_make_message("hw_imei", "null")]
        raw = collect_raw_values(msgs)
        assert raw.get("hw_imei") is None or raw["hw_imei"] == []

    def test_raw_values_empty_on_no_messages(self):
        raw = collect_raw_values([])
        assert raw == {}

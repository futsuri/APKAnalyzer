"""Сборка объектов Finding из сырых Frida-сообщений.

Чистые функции (без IO), легко тестируемые с моками.
Маскирование по mask_strategy из каталога — здесь.
"""

from __future__ import annotations

import logging
from typing import Any

from src.dynamic.masking import mask_value
from src.models.analysis import Finding, FindingOccurrence
from src.static.catalog import CatalogIdentifier

logger = logging.getLogger(__name__)


def build_findings(
    messages: list[dict[str, Any]],
    catalog: list[CatalogIdentifier],
) -> dict[str, Finding]:
    """Строит словарь ``{identifier_id: Finding}`` из сырых Frida-сообщений.

    Для каждого identifier_id из каталога создаётся Finding:
      - ``found = True`` если есть ≥1 сообщение с этим identifier_id
      - ``occurrences`` — дедуплицированный список вызовов (маскированные значения)
      - ``frida_hook`` — копируется из каталога
      - ``traffic_detection`` — пустой ``{}`` (задел под СПМ-2)

    Args:
        messages: список payload из ``send({...})`` Frida-скрипта.
        catalog: полный каталог идентификаторов.

    Returns:
        ``{identifier_id: Finding}``
    """
    # Группируем сообщения по identifier_id
    grouped: dict[str, list[dict[str, Any]]] = {}
    for msg in messages:
        id_key = msg.get("identifier_id", "")
        if not id_key:
            continue
        grouped.setdefault(id_key, []).append(msg)

    # Строим Finding для каждой записи каталога
    catalog_by_id = {c.identifier_id: c for c in catalog}
    findings: dict[str, Finding] = {}

    for entry in catalog:
        identifier_id = entry.identifier_id
        msgs = grouped.get(identifier_id, [])
        hook_cfg = entry.frida_hook or {}
        strategy = hook_cfg.get("mask_strategy", "plain")

        # Дедупликация по значению
        seen_values: set[str] = set()
        occurrences: list[FindingOccurrence] = []

        for msg in msgs:
            raw_value = _coerce_str(msg.get("value"))
            if not raw_value or raw_value in ("null", "undefined"):
                continue
            if raw_value in seen_values:
                continue
            seen_values.add(raw_value)

            masked = mask_value(raw_value, strategy, identifier_id)
            stack = _coerce_str(msg.get("stack", ""))
            method = _coerce_str(msg.get("method", ""))

            occurrences.append(FindingOccurrence(
                file="dynamic",
                line=0,
                code=f"{method}: {masked}",
                is_third_party=False,
                package_guess=None,
            ))

        findings[identifier_id] = Finding(
            identifier_id=identifier_id,
            name=entry.name,
            category=entry.category,
            severity=entry.severity,
            description=entry.description,
            permissions=list(entry.permissions),
            found=len(occurrences) > 0,
            matched_signature=hook_cfg.get("class") if occurrences else None,
            occurrences=occurrences,
            permissions_present_in_manifest=False,  # нет доступа к манифесту в динамике
            frida_hook=hook_cfg,
            traffic_detection={},  # задел под СПМ-2
        )

    return findings


def collect_raw_values(
    messages: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Собирает **немаскированные** значения для технического файла.

    Задел под будущую сверку с трафик-модулем (СПМ-2).
    """
    raw: dict[str, list[str]] = {}
    for msg in messages:
        id_key = msg.get("identifier_id", "")
        value = _coerce_str(msg.get("value"))
        if not id_key or not value or value in ("null", "undefined"):
            continue
        raw.setdefault(id_key, []).append(value)
    return raw


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce_str(val: Any) -> str:
    """Приводит значение к строке."""
    if val is None:
        return ""
    return str(val)

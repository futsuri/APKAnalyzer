"""Маскирование значений идентификаторов по стратегиям из identifiers_catalog.yaml."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def mask_value(value: str, strategy: Optional[str], identifier_id: str = "") -> str:
    """Маскирует сырой значение идентификатора согласно стратегии из каталога.

    Поддерживаемые стратегии:
      - ``plain``           — значение возвращается как есть
      - ``sha256``           — hex-дайджест SHA-256
      - ``md5``              — hex-дайджест MD5
      - ``mac_anonymize``    — MAC-адрес с занулением средней части
                               (AA:BB:CC:DD:EE:FF → AA:BB:00:00:EE:FF)
      - ``custom_phone_mask``— телефон с маскировкой средней части
                               (+79998887766 → +7999******66)

    Неизвестная стратегия → fallback на ``plain`` + warning.
    """
    if not value:
        return value

    if strategy == "plain" or strategy is None:
        return value

    if strategy == "sha256":
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    if strategy == "md5":
        return hashlib.md5(value.encode("utf-8")).hexdigest()

    if strategy == "mac_anonymize":
        return _mask_mac(value, identifier_id)

    if strategy == "custom_phone_mask":
        return _mask_phone(value, identifier_id)

    logger.warning(
        "Неизвестная стратегия маскирования '%s' для %s, используется plain",
        strategy,
        identifier_id,
    )
    return value


# ---------------------------------------------------------------------------
# Внутренние helpers
# ---------------------------------------------------------------------------

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{2}):"
                      r"([0-9A-Fa-f]{2}):([0-9A-Fa-f]{2}):"
                      r"([0-9A-Fa-f]{2}):([0-9A-Fa-f]{2})$")


def _mask_mac(value: str, identifier_id: str = "") -> str:
    """Зануляет третий и четвёртый октет MAC-адреса.

    Пример: AA:BB:CC:DD:EE:FF → AA:BB:00:00:EE:FF
    Если формат не MAC — возвращает SHA-256 (safe fallback).
    """
    m = _MAC_RE.match(value.strip())
    if not m:
        logger.warning(
            "Значение '%s' для %s не похоже на MAC, используется sha256",
            value, identifier_id,
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
    parts = list(m.groups())
    parts[2] = "00"
    parts[3] = "00"
    return ":".join(parts)


def _mask_phone(value: str, identifier_id: str = "") -> str:
    """Маскирует номер телефона, сохраняя код страны и последние цифры.

    Стратегия: оставляем первые 4 и последние 2 символа, середина — '*'.
    Пример: +79998887766 → +799******66
    Для коротких значений (<8 символов) — SHA-256.
    """
    digits = re.sub(r"\D", "", value)
    if len(digits) < 8:
        logger.warning(
            "Номер '%s' для %s слишком короткий, используется sha256",
            value, identifier_id,
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    # Маска: первые 4 цифры, последние 2, середина — звёздочки
    # Пример: 11 цифр → 4 + 5 + 2 = 11 ✓
    masked_digits = digits[:4] + "*" * (len(digits) - 6) + digits[-2:]

    # Восстанавливаем формат: вставляем маскированные цифры вместо оригинальных
    result = []
    digit_idx = 0
    for ch in value:
        if ch.isdigit():
            result.append(masked_digits[digit_idx])
            digit_idx += 1
        else:
            result.append(ch)
    return "".join(result)

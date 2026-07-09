from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CatalogIdentifier:
    identifier_id: str
    name: str
    category: str
    severity: str
    description: str | None = None
    permissions: list[str] = field(default_factory=list)
    static_signatures: list[str] = field(default_factory=list)
    frida_hook: dict[str, Any] | None = None
    traffic_detection: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CatalogIdentifier":
        return cls(
            identifier_id=data["id"],
            name=data["name"],
            category=data["category"],
            severity=str(data["severity"]),
            description=data.get("description"),
            permissions=list(data.get("permissions", [])),
            static_signatures=list(data["static_signatures"]),
            frida_hook=data.get("frida_hook"),
            traffic_detection=data.get("traffic_detection"),
        )


def _default_catalog_path() -> Path:
    return Path(__file__).resolve().parents[2] / "identifiers_catalog.yaml"


def load_identifiers_catalog(path: Path | None = None) -> list[CatalogIdentifier]:
    catalog_path = path or _default_catalog_path()
    raw = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    items = raw.get("identifiers")

    if not isinstance(items, list):
        raise ValueError(f"Invalid catalog format in {catalog_path}: 'identifiers' must be a list")

    required_fields = ("id", "name", "category", "severity", "static_signatures")
    identifiers: list[CatalogIdentifier] = []

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Catalog entry #{index} must be a mapping")
        for field_name in required_fields:
            if field_name not in item:
                raise ValueError(f"Catalog entry #{index} is missing required field: {field_name}")
        if not isinstance(item["static_signatures"], list) or not item["static_signatures"]:
            raise ValueError(
                f"Catalog entry #{index} field 'static_signatures' must be a non-empty list"
            )
        identifiers.append(CatalogIdentifier.from_dict(item))

    return identifiers

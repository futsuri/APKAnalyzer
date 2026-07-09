from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _as_risk_level(value: RiskLevel | str | None, default: RiskLevel) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    if isinstance(value, str):
        try:
            return RiskLevel(value)
        except ValueError:
            return default
    return default


@dataclass
class Permission:
    name: str
    is_dangerous: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    description: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Permission":
        return cls(
            name=data.get("name", ""),
            is_dangerous=bool(data.get("is_dangerous", False)),
            risk_level=_as_risk_level(data.get("risk_level"), RiskLevel.LOW),
            description=data.get("description"),
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "is_dangerous": self.is_dangerous,
            "risk_level": self.risk_level.value,
            "description": self.description,
        }


@dataclass
class Component:
    name: str
    exported: bool = False
    type: str = "activity"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Component":
        return cls(
            name=data.get("name", ""),
            exported=bool(data.get("exported", False)),
            type=data.get("type", "activity"),
        )

    def model_dump(self) -> dict[str, Any]:
        return {"name": self.name, "exported": self.exported, "type": self.type}


@dataclass
class Secret:
    type: str
    value: str
    location: str
    risk_level: RiskLevel = RiskLevel.MEDIUM

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Secret":
        return cls(
            type=data.get("type", "unknown"),
            value=data.get("value", ""),
            location=data.get("location", ""),
            risk_level=_as_risk_level(data.get("risk_level"), RiskLevel.MEDIUM),
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "value": self.value,
            "location": self.location,
            "risk_level": self.risk_level.value,
        }


@dataclass
class Identifier:
    name: str
    found: bool = False
    locations: list[dict[str, Any]] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "Identifier":
        return cls(
            name=name,
            found=bool(data.get("found", False)),
            locations=list(data.get("locations", [])),
            risk_level=_as_risk_level(data.get("risk_level"), RiskLevel.LOW),
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "found": self.found,
            "locations": self.locations,
            "risk_level": self.risk_level.value,
        }


@dataclass
class FindingOccurrence:
    file: str
    line: int
    code: str
    is_third_party: bool
    package_guess: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FindingOccurrence":
        return cls(
            file=data.get("file", ""),
            line=int(data.get("line", 0) or 0),
            code=data.get("code", ""),
            is_third_party=bool(data.get("is_third_party", False)),
            package_guess=data.get("package_guess"),
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "code": self.code,
            "is_third_party": self.is_third_party,
            "package_guess": self.package_guess,
        }


@dataclass
class Finding:
    identifier_id: str
    name: str
    category: str
    severity: str
    description: str | None = None
    permissions: list[str] = field(default_factory=list)
    found: bool = False
    matched_signature: str | None = None
    occurrences: list[FindingOccurrence] = field(default_factory=list)
    permissions_present_in_manifest: bool = False
    frida_hook: dict[str, Any] | None = None
    traffic_detection: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Finding":
        return cls(
            identifier_id=data.get("identifier_id", ""),
            name=data.get("name", ""),
            category=data.get("category", "unknown"),
            severity=str(data.get("severity", "LOW")),
            description=data.get("description"),
            permissions=list(data.get("permissions", [])),
            found=bool(data.get("found", False)),
            matched_signature=data.get("matched_signature"),
            occurrences=[
                FindingOccurrence.from_dict(item) for item in data.get("occurrences", [])
            ],
            permissions_present_in_manifest=bool(
                data.get("permissions_present_in_manifest", False)
            ),
            frida_hook=data.get("frida_hook"),
            traffic_detection=data.get("traffic_detection"),
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "identifier_id": self.identifier_id,
            "name": self.name,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "permissions": self.permissions,
            "found": self.found,
            "matched_signature": self.matched_signature,
            "occurrences": [occurrence.model_dump() for occurrence in self.occurrences],
            "permissions_present_in_manifest": self.permissions_present_in_manifest,
            "frida_hook": self.frida_hook,
            "traffic_detection": self.traffic_detection,
        }


@dataclass
class Manifest:
    package: str = "unknown"
    version_code: str = "0"
    version_name: str = "unknown"
    min_sdk: int = 0
    target_sdk: int = 0
    permissions: list[Permission] = field(default_factory=list)
    activities: list[Component] = field(default_factory=list)
    services: list[Component] = field(default_factory=list)
    receivers: list[Component] = field(default_factory=list)
    providers: list[Component] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Manifest":
        return cls(
            package=data.get("package", "unknown"),
            version_code=str(data.get("version_code", "0")),
            version_name=data.get("version_name", "unknown"),
            min_sdk=int(data.get("min_sdk", 0) or 0),
            target_sdk=int(data.get("target_sdk", 0) or 0),
            permissions=[Permission.from_dict(p) for p in data.get("permissions", [])],
            activities=[Component.from_dict(c) for c in data.get("activities", [])],
            services=[Component.from_dict(c) for c in data.get("services", [])],
            receivers=[Component.from_dict(c) for c in data.get("receivers", [])],
            providers=[Component.from_dict(c) for c in data.get("providers", [])],
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "package": self.package,
            "version_code": self.version_code,
            "version_name": self.version_name,
            "min_sdk": self.min_sdk,
            "target_sdk": self.target_sdk,
            "permissions": [permission.model_dump() for permission in self.permissions],
            "activities": [component.model_dump() for component in self.activities],
            "services": [component.model_dump() for component in self.services],
            "receivers": [component.model_dump() for component in self.receivers],
            "providers": [component.model_dump() for component in self.providers],
        }


@dataclass
class AnalysisResult:
    apk_file: str
    manifest: Manifest | None = None
    identifiers: dict[str, Finding] = field(default_factory=dict)
    secrets: list[Secret] = field(default_factory=list)
    libraries: list[str] = field(default_factory=list)
    summary: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisResult":
        manifest_data = data.get("manifest")
        raw_identifiers = data.get("identifiers", {})
        parsed_identifiers: dict[str, Finding] = {}
        for key, value in raw_identifiers.items():
            value = dict(value)
            if "identifier_id" not in value:
                value["identifier_id"] = key
            parsed_identifiers[key] = Finding.from_dict(value)

        return cls(
            apk_file=data.get("apk_file", ""),
            manifest=Manifest.from_dict(manifest_data) if manifest_data else None,
            identifiers=parsed_identifiers,
            secrets=[Secret.from_dict(secret) for secret in data.get("secrets", [])],
            libraries=list(data.get("libraries", [])),
            summary=data.get("summary"),
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "apk_file": self.apk_file,
            "manifest": self.manifest.model_dump() if self.manifest else None,
            "identifiers": {
                name: identifier.model_dump() for name, identifier in self.identifiers.items()
            },
            "secrets": [secret.model_dump() for secret in self.secrets],
            "libraries": self.libraries,
            "summary": self.summary,
        }

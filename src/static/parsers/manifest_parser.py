import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from src.core.config import DANGEROUS_PERMISSIONS
from src.models.analysis import Component, Manifest, Permission

logger = logging.getLogger(__name__)

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


def _android_attr(name: str) -> str:
    return f"{ANDROID_NS}{name}"


def _to_int(value: str | None) -> int:
    try:
        return int(value or "0")
    except (TypeError, ValueError):
        return 0


def _permission_meta(permission_name: str) -> tuple[bool, str | None]:
    short_name = permission_name.split(".")[-1]
    description = DANGEROUS_PERMISSIONS.get(permission_name) or DANGEROUS_PERMISSIONS.get(short_name)
    return description is not None, description


class ManifestParser:
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path

    def parse(self) -> Manifest | None:
        if not self.manifest_path.exists():
            logger.error(f"Манифест не найден: {self.manifest_path}")
            return None

        try:
            tree = ET.parse(self.manifest_path)
            root = tree.getroot()
        except ET.ParseError as error:
            logger.error(f"Ошибка парсинга манифеста: {error}")
            return None

        manifest = Manifest(
            package=root.get("package", "unknown"),
            version_code=root.get(_android_attr("versionCode"), "0"),
            version_name=root.get(_android_attr("versionName"), "unknown"),
        )

        uses_sdk = root.find("uses-sdk")
        if uses_sdk is not None:
            manifest.min_sdk = _to_int(uses_sdk.get(_android_attr("minSdkVersion")))
            manifest.target_sdk = _to_int(uses_sdk.get(_android_attr("targetSdkVersion")))

        for permission_node in root.findall("uses-permission"):
            name = permission_node.get(_android_attr("name"), "")
            if not name:
                continue
            is_dangerous, description = _permission_meta(name)
            manifest.permissions.append(
                Permission(name=name, is_dangerous=is_dangerous, description=description)
            )

        application = root.find("application")
        if application is not None:
            for tag, target in (
                ("activity", manifest.activities),
                ("service", manifest.services),
                ("receiver", manifest.receivers),
                ("provider", manifest.providers),
            ):
                for node in application.findall(tag):
                    name = node.get(_android_attr("name"), "")
                    if not name:
                        continue
                    target.append(
                        Component(
                            name=name,
                            exported=node.get(_android_attr("exported"), "false").lower() == "true",
                            type=tag,
                        )
                    )

        return manifest
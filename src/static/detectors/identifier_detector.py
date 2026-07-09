from __future__ import annotations

import logging
import re
from pathlib import Path

from src.static.catalog import CatalogIdentifier

logger = logging.getLogger(__name__)

_LIB_PREFIXES = ("android", "androidx", "java", "javax", "kotlin")


class IdentifierDetector:
    def __init__(
        self,
        jadx_source_dir: Path | None,
        apktool_dir: Path | None,
        catalog: list[CatalogIdentifier],
        app_package: str | None = None,
        manifest_permissions: list[str] | None = None,
    ):
        self.jadx_source_dir = jadx_source_dir
        self.apktool_dir = apktool_dir
        self.catalog = catalog
        self.app_package = app_package or ""
        self.manifest_permissions = set(manifest_permissions or [])
        self.results = {
            item.identifier_id: {
                "identifier_id": item.identifier_id,
                "name": item.name,
                "category": item.category,
                "severity": item.severity,
                "description": item.description,
                "permissions": item.permissions,
                "found": False,
                "matched_signature": None,
                "occurrences": [],
                "permissions_present_in_manifest": self._permissions_present(item.permissions),
                "frida_hook": item.frida_hook,
                "traffic_detection": item.traffic_detection,
            }
            for item in catalog
        }

    def scan(self) -> dict:
        files = self._collect_files()
        logger.info(f"Сканирование {len(files)} файлов на идентификаторы")

        for file_path in files:
            self._scan_file(file_path)

        for finding in self.results.values():
            finding["found"] = bool(finding["occurrences"])

        return self.results

    def _collect_files(self) -> list[Path]:
        files: list[Path] = []

        if self.apktool_dir and self.apktool_dir.exists():
            files.extend(self.apktool_dir.glob("smali*/**/*.smali"))
            files.extend(self.apktool_dir.glob("res/values/*.xml"))
            manifest_path = self.apktool_dir / "AndroidManifest.xml"
            if manifest_path.exists():
                files.append(manifest_path)

        if self.jadx_source_dir and self.jadx_source_dir.exists():
            files.extend(self.jadx_source_dir.rglob("*.java"))

        return files

    def _scan_file(self, file_path: Path):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        lines = content.splitlines()
        relative_path = self._relative_path(file_path)
        file_kind = self._file_kind(file_path)
        in_block_comment = False

        for line_number, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            line, in_block_comment = self._normalize_line_for_match(file_kind, line, in_block_comment)
            if not line:
                continue

            for item in self.catalog:
                for signature in item.static_signatures:
                    if not self._line_matches_signature(line, signature):
                        continue
                    occurrence = {
                        "file": relative_path,
                        "line": line_number,
                        "code": raw_line.strip()[:240],
                        "is_third_party": self._is_third_party(relative_path),
                        "package_guess": self._guess_package(relative_path),
                    }
                    finding = self.results[item.identifier_id]
                    finding["occurrences"].append(occurrence)
                    if finding["matched_signature"] is None:
                        finding["matched_signature"] = signature

    @staticmethod
    def _file_kind(file_path: Path) -> str:
        if file_path.suffix == ".smali":
            return "smali"
        if file_path.suffix == ".xml":
            return "xml"
        return "java"

    @staticmethod
    def _normalize_line_for_match(
        file_kind: str, line: str, in_block_comment: bool
    ) -> tuple[str, bool]:
        if not line:
            return "", in_block_comment

        if file_kind == "smali":
            return ("", in_block_comment) if line.startswith("#") else (line, in_block_comment)

        if file_kind == "xml":
            if in_block_comment:
                if "-->" in line:
                    return "", False
                return "", True
            if line.startswith("<!--") and "-->" not in line:
                return "", True
            if line.startswith("<!--"):
                return "", False
            return line, False

        # java-like comments
        if in_block_comment:
            if "*/" in line:
                _, tail = line.split("*/", 1)
                return IdentifierDetector._normalize_line_for_match(file_kind, tail.strip(), False)
            return "", True

        if line.startswith("/*"):
            if "*/" in line:
                _, tail = line.split("*/", 1)
                return tail.strip(), False
            return "", True
        if line.startswith("//") or line.startswith("*"):
            return "", False

        return line, False

    @staticmethod
    def _line_matches_signature(line: str, signature: str) -> bool:
        signature = signature.strip()
        if not signature:
            return False

        # Smali style signatures.
        if signature.startswith("L") and (";->" in signature or ":" in signature):
            return signature in line

        if signature.endswith("("):
            method = re.escape(signature[:-1])
            return re.search(rf"\b{method}\s*\(", line) is not None

        if "://" in signature:
            return signature in line

        if re.search(r"[^a-zA-Z0-9_.$]", signature):
            return signature in line

        token = re.escape(signature)
        return re.search(rf"\b{token}\b", line, re.IGNORECASE) is not None

    def _relative_path(self, file_path: Path) -> str:
        if self.apktool_dir and self.apktool_dir in file_path.parents:
            return str(file_path.relative_to(self.apktool_dir.parent))
        if self.jadx_source_dir and self.jadx_source_dir in file_path.parents:
            return str(file_path.relative_to(self.jadx_source_dir.parent))
        return str(file_path)

    def _guess_package(self, relative_path: str) -> str | None:
        parts = Path(relative_path).parts
        if not parts:
            return None

        if parts[0].startswith("smali"):
            package_parts = parts[1:-1]
            if package_parts:
                return ".".join(package_parts)
            return None

        if parts[0] == "sources":
            package_parts = parts[1:-1]
            if package_parts:
                return ".".join(package_parts)
            return None

        if parts[0] in {"AndroidManifest.xml", "res"}:
            return self.app_package or None

        return None

    def _is_third_party(self, relative_path: str) -> bool:
        package_guess = self._guess_package(relative_path)
        if not package_guess:
            return False

        if package_guess.startswith(_LIB_PREFIXES):
            return True

        if not self.app_package:
            return False

        if package_guess == self.app_package or package_guess.startswith(f"{self.app_package}."):
            return False

        app_root = ".".join(self.app_package.split(".")[:2])
        if app_root and (
            package_guess == app_root or package_guess.startswith(f"{app_root}.")
        ):
            return False

        return True

    def _permissions_present(self, permissions: list[str]) -> bool:
        if not permissions:
            return True
        return set(permissions).issubset(self.manifest_permissions)

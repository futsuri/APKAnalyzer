from __future__ import annotations

from pathlib import Path

import pytest

from src.static.catalog import CatalogIdentifier, load_identifiers_catalog
from src.static.detectors.identifier_detector import IdentifierDetector


def _catalog() -> list[CatalogIdentifier]:
    root = Path(__file__).resolve().parents[1]
    return load_identifiers_catalog(root / "identifiers_catalog.yaml")


def _write_manifest(path: Path, permissions: list[str]):
    perms = "\n".join(
        f'    <uses-permission android:name="{permission}" />' for permission in permissions
    )
    content = f"""<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.example.app">
{perms}
<application />
</manifest>
"""
    path.write_text(content, encoding="utf-8")


def _render_code_for_signature(signature: str) -> tuple[str, str]:
    if signature.startswith("L") and (";->" in signature or ":" in signature):
        if ":" in signature:
            return (
                "smali/com/example/app/MainActivity.smali",
                f"sget-object v0, {signature}",
            )
        return (
            "smali/com/example/app/MainActivity.smali",
            f"invoke-virtual {{v0}}, {signature}()V",
        )

    if signature.endswith("("):
        method_name = signature[:-1]
        return (
            "sources/com/example/app/MainActivity.java",
            f"String value = obj.{method_name}();",
        )

    if "://" in signature:
        return (
            "sources/com/example/app/MainActivity.java",
            f'String uri = "{signature}";',
        )

    return (
        "sources/com/example/app/MainActivity.java",
        f'String marker = "{signature}";',
    )


def _render_comment_for_signature(signature: str) -> tuple[str, str]:
    if signature.startswith("L") and (";->" in signature or ":" in signature):
        return (
            "smali/com/example/app/CommentOnly.smali",
            f"# {signature}",
        )
    return (
        "sources/com/example/app/CommentOnly.java",
        f"// {signature}",
    )


def _run_detector(base_dir: Path, permissions: list[str]) -> dict:
    apktool_dir = base_dir / "apktool"
    jadx_dir = base_dir / "jadx_output"
    apktool_dir.mkdir(parents=True, exist_ok=True)
    jadx_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = apktool_dir / "AndroidManifest.xml"
    _write_manifest(manifest_path, permissions)

    detector = IdentifierDetector(
        jadx_source_dir=jadx_dir,
        apktool_dir=apktool_dir,
        catalog=_catalog(),
        app_package="com.example.app",
        manifest_permissions=permissions,
    )
    return detector.scan()


@pytest.mark.parametrize("entry", _catalog(), ids=lambda item: item.identifier_id)
def test_identifier_detector_positive_for_each_catalog_entry(tmp_path: Path, entry: CatalogIdentifier):
    target_path, matched_line = _render_code_for_signature(entry.static_signatures[0])
    file_path = tmp_path / "apktool" / target_path if target_path.startswith("smali/") else tmp_path / "jadx_output" / target_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(matched_line + "\n", encoding="utf-8")

    results = _run_detector(tmp_path, entry.permissions)
    finding = results[entry.identifier_id]

    assert finding["found"] is True
    assert finding["matched_signature"] in entry.static_signatures
    assert finding["occurrences"], "Expected at least one occurrence"
    assert finding["permissions_present_in_manifest"] is True


@pytest.mark.parametrize("entry", _catalog(), ids=lambda item: item.identifier_id)
def test_identifier_detector_ignores_comment_only_signature(tmp_path: Path, entry: CatalogIdentifier):
    target_path, comment_line = _render_comment_for_signature(entry.static_signatures[0])
    file_path = tmp_path / "apktool" / target_path if target_path.startswith("smali/") else tmp_path / "jadx_output" / target_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(comment_line + "\n", encoding="utf-8")

    results = _run_detector(tmp_path, [])
    finding = results[entry.identifier_id]

    assert finding["found"] is False
    assert finding["occurrences"] == []


def test_identifier_detector_returns_all_catalog_entries_when_no_matches(tmp_path: Path):
    results = _run_detector(tmp_path, [])
    catalog_ids = {item.identifier_id for item in _catalog()}
    result_ids = set(results.keys())

    assert result_ids == catalog_ids
    assert all(not finding["found"] for finding in results.values())


def test_identifier_detector_marks_permission_signal_when_permissions_missing(tmp_path: Path):
    entry = next(item for item in _catalog() if item.permissions)
    target_path, matched_line = _render_code_for_signature(entry.static_signatures[0])
    file_path = tmp_path / "apktool" / target_path if target_path.startswith("smali/") else tmp_path / "jadx_output" / target_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(matched_line + "\n", encoding="utf-8")

    results = _run_detector(tmp_path, [])
    finding = results[entry.identifier_id]

    assert finding["found"] is True
    assert finding["permissions_present_in_manifest"] is False

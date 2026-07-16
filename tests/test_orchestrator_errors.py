"""Тесты обработки ошибок оркестратора.

Проверяет, что при недоступном эмуляторе/frida оркестратор возвращает
результат с errors, не кидая исключение наружу.
Без реального устройства — моки.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.dynamic.orchestrator import DynamicOrchestrator
from src.dynamic.emulator_controller import (
    AdbConnectionError, ApkInstallError, EmulatorError, EmulatorController,
)
from src.dynamic.frida_manager import FridaError, FridaManager


def _make_apk(tmp_path: Path) -> Path:
    apk = tmp_path / "test.apk"
    apk.write_bytes(b"PK" + b"\x00" * 100)
    return apk


class TestOrchestratorEmulatorUnavailable:
    """Эмулятор недоступен → результат с errors, без исключения."""

    def test_connect_failure_returns_errors(self, tmp_path):
        with patch.object(EmulatorController, "connect", side_effect=AdbConnectionError("connection refused")):
            orch = DynamicOrchestrator()
            apk = _make_apk(tmp_path)
            result = orch.run(apk, "com.example.app")

        assert len(result.errors) > 0
        assert any("Подключение к эмулятору" in e for e in result.errors)
        # Контракт: findings всегда содержит все 13 записей каталога (found=False при ошибке)
        assert len(result.findings) == 13
        assert all(not f.found for f in result.findings.values())

    def test_adb_missing_returns_errors(self, tmp_path):
        with patch.object(EmulatorController, "connect", side_effect=EmulatorError("adb not found")):
            orch = DynamicOrchestrator()
            apk = _make_apk(tmp_path)
            result = orch.run(apk, "com.example.app")

        assert len(result.errors) > 0

    def test_boot_timeout_returns_errors(self, tmp_path):
        with patch.object(EmulatorController, "connect", return_value=True), \
             patch.object(EmulatorController, "wait_for_boot", side_effect=EmulatorError("boot timeout")):
            orch = DynamicOrchestrator()
            apk = _make_apk(tmp_path)
            result = orch.run(apk, "com.example.app")

        assert len(result.errors) > 0
        assert any("Ожидание устройства" in e for e in result.errors)


class TestOrchestratorFridaUnavailable:
    """Frida недоступна → результат с errors, приложение запускается без хуков."""

    def test_frida_failure_returns_errors_no_crash(self, tmp_path):
        with patch.object(EmulatorController, "connect", return_value=True), \
             patch.object(EmulatorController, "wait_for_boot", return_value=True), \
             patch.object(EmulatorController, "install_apk", return_value=True), \
             patch.object(EmulatorController, "start_app", return_value=True), \
             patch.object(EmulatorController, "stop_app"), \
             patch.object(FridaManager, "attach",
                          side_effect=FridaError("frida-server not reachable")):
            orch = DynamicOrchestrator()
            apk = _make_apk(tmp_path)
            result = orch.run(apk, "com.example.app")

        assert len(result.errors) > 0
        assert any("Frida" in e for e in result.errors)
        assert result.findings != {}  # все 13 из каталога, но found=False


class TestOrchestratorNoException:
    """Любая ошибка в pipeline → DynamicResult с errors, без propagate."""

    def test_apk_install_error_no_exception(self, tmp_path):
        with patch.object(EmulatorController, "connect", return_value=True), \
             patch.object(EmulatorController, "wait_for_boot", return_value=True), \
             patch.object(EmulatorController, "install_apk",
                          side_effect=ApkInstallError("install failed")):
            orch = DynamicOrchestrator()
            apk = _make_apk(tmp_path)
            result = orch.run(apk, "com.example.app")

        assert isinstance(result.errors, list)
        assert len(result.errors) > 0
        assert any("Установка APK" in e for e in result.errors)

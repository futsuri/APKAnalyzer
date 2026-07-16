"""Главный оркестратор динамического анализа.

Результат — ``{identifier_id: Finding}``, совместимый со статикой.
Ошибки собираются в ``errors``, pipeline не падает исключением наружу.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.core.config import DYNAMIC_OUTPUT_DIR, TEMP_DIR
from src.dynamic.emulator_controller import (
    AdbConnectionError,
    ApkInstallError,
    DeviceNotReadyError,
    EmulatorController,
    EmulatorError,
)
from src.dynamic.finding_builder import build_findings, collect_raw_values
from src.dynamic.frida_manager import (
    FridaError,
    FridaServerNotReachable,
    FridaUnavailableError,
    FridaManager,
    ProcessAttachError,
)
from src.dynamic.hook_generator import generate_hook_script, save_hook_script
from src.dynamic.runner import MonkeyRunner
from src.static.catalog import load_identifiers_catalog

logger = logging.getLogger(__name__)


class _AbortPipeline(Exception):
    """Внутренний sentinel: ранний выход из pipeline без исключения наружу."""


# ---------------------------------------------------------------------------
# Результат оркестратора
# ---------------------------------------------------------------------------

@dataclass
class DynamicResult:
    """Результат динамического анализа."""
    apk: str = ""
    package: str = ""
    timestamp: str = ""
    findings: dict[str, Any] = field(default_factory=dict)  # {identifier_id: Finding}
    raw_values: dict[str, list[str]] = field(default_factory=dict)
    raw_values_path: Optional[Path] = None
    errors: list[str] = field(default_factory=list)
    logcat: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# DynamicOrchestrator
# ---------------------------------------------------------------------------

class DynamicOrchestrator:
    """Оркестратор динамического анализа APK."""

    def __init__(
        self,
        catalog: Optional[list] = None,
        emulator_host: Optional[str] = None,
        runner=None,
        frida_timeout: float = 60.0,
    ):
        self.catalog = catalog or load_identifiers_catalog()
        self.emulator = EmulatorController(host=emulator_host)
        self.frida = FridaManager(host=emulator_host)
        self.runner = runner or MonkeyRunner()
        self.frida_timeout = frida_timeout

    def run(self, apk_path: Path, package_name: str) -> DynamicResult:
        """Запускает полный динамический анализ.

        Pipeline не падает исключением — все ошибки собираются в
        ``DynamicResult.errors``.
        """
        result = DynamicResult(
            apk=str(apk_path),
            package=package_name,
            timestamp=datetime.now().isoformat(),
        )

        logger.info("=" * 60)
        logger.info("ДИНАМИЧЕСКИЙ АНАЛИЗ: %s (%s)", apk_path.name, package_name)
        logger.info("=" * 60)

        messages: list[dict[str, Any]] = []

        try:
            # 1. Подключение к эмулятору
            try:
                self.emulator.connect()
            except (AdbConnectionError, EmulatorError) as e:
                result.errors.append(f"Подключение к эмулятору: {e}")
                raise _AbortPipeline

            # 2. Ожидание загрузки
            try:
                self.emulator.wait_for_boot()
            except (DeviceNotReadyError, EmulatorError) as e:
                result.errors.append(f"Ожидание устройства: {e}")
                raise _AbortPipeline

            # 3. Установка APK
            try:
                self.emulator.install_apk(apk_path)
            except (ApkInstallError, EmulatorError) as e:
                result.errors.append(f"Установка APK: {e}")
                raise _AbortPipeline

            # 4. Генерация хуков из каталога
            script_source = generate_hook_script(self.catalog)
            script_path = TEMP_DIR / "frida_hooks_generated.js"
            save_hook_script(script_source, script_path)

            # 5. Запуск приложения + Attach Frida
            try:
                self.emulator.start_app(package_name)
                logger.info("Приложение запущено: %s", package_name)
            except EmulatorError as e:
                result.errors.append(f"Запуск приложения: {e}")
                raise _AbortPipeline

            try:
                self.frida.attach(package_name, script_source)
                logger.info("Frida attached к %s", package_name)
            except (FridaUnavailableError, FridaServerNotReachable,
                    ProcessAttachError, FridaError) as e:
                result.errors.append(f"Frida: {e}")
                raise _AbortPipeline

            # 6. Monkey-прогон (Frida уже хукает)
            try:
                self.runner.run(self.emulator, package_name)
            except Exception as e:
                result.errors.append(f"Monkey-прогон: {e}")

            # 7. Сбор сообщений
            time.sleep(2)  # финальный flush
            messages = self.frida.get_messages()
            logger.info("Собрано %d Frida-сообщений", len(messages))

            # 8. Сбор logcat
            try:
                logcat = self.emulator.get_logcat()
                result.logcat = logcat.split("\n") if logcat else []
            except EmulatorError:
                pass

        except _AbortPipeline:
            logger.info("Pipeline прерван на раннем этапе (ошибки в result.errors)")
        finally:
            # ВСЕГДА строим findings из каталога (с пустыми messages — все found=False)
            result.findings = build_findings(messages, self.catalog)
            result.raw_values = collect_raw_values(messages)

            # Остановка и очистка
            try:
                self.emulator.stop_app(package_name)
            except Exception:
                pass

            try:
                self.frida.disconnect()
            except Exception as e:
                logger.debug("Ошибка отключения Frida: %s", e)

            # Сохраняем немаскированные значения в технический файл
            if result.raw_values:
                raw_path = self._save_raw_values(result)
                result.raw_values_path = raw_path

        found_count = sum(1 for f in result.findings.values() if f.found)
        logger.info("Найдено идентификаторов: %d/%d", found_count, len(self.catalog))

        logger.info("=" * 60)
        logger.info("АНАЛИЗ ЗАВЕРШЁН: найдено %d, ошибок %d",
                     found_count, len(result.errors))
        logger.info("=" * 60)

        return result

    def _save_raw_values(self, result: DynamicResult) -> Path:
        """Сохраняет немаскированные значения в технический JSON."""
        DYNAMIC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{Path(result.apk).stem}_raw_values.json"
        filepath = DYNAMIC_OUTPUT_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.raw_values, f, indent=2, ensure_ascii=False)

        logger.info("Немаскированные значения: %s", filepath)
        return filepath

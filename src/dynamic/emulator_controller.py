"""Управление эмулятором Android через ADB по сети.

Единый сетевой транспорт: ``adb connect <host>:<port>`` вместо ``docker exec``.
Хост эмулятора — параметр / env ``EMULATOR_HOST``, не хардкод.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Исключения
# ---------------------------------------------------------------------------

class EmulatorError(Exception):
    """Базовое исключение модуля эмулятора."""


class AdbConnectionError(EmulatorError):
    """Не удалось подключиться к ADB."""


class DeviceNotReadyError(EmulatorError):
    """Устройство не загрузилось."""


class ApkInstallError(EmulatorError):
    """Не удалось установить APK."""


# ---------------------------------------------------------------------------
# EmulatorController
# ---------------------------------------------------------------------------

class EmulatorController:
    """Управление эмулятором через сетевой ADB (без docker exec)."""

    def __init__(
        self,
        host: Optional[str] = None,
        adb_port: int = 5555,
        frida_port: int = 27042,
    ):
        self.host = host or os.getenv("EMULATOR_HOST", "android-emulator")
        self.adb_port = adb_port
        self.frida_port = frida_port
        self.device_serial = f"{self.host}:{self.adb_port}"
        self._connected = False

        logger.info(
            "EmulatorController: host=%s, adb_port=%d, frida_port=%d, serial=%s",
            self.host, self.adb_port, self.frida_port, self.device_serial,
        )

    # ------------------------------------------------------------------
    # Внутренняя обёртка ADB
    # ------------------------------------------------------------------

    def _adb(self, args: str, timeout: int = 30) -> str:
        """Выполняет adb-команду, целевой девайс через -s <serial>."""
        cmd = f"adb -s {self.device_serial} {args}"
        logger.debug("adb: %s", cmd)
        try:
            result = subprocess.check_output(
                cmd, shell=True, text=True, timeout=timeout,
                stderr=subprocess.STDOUT,
            )
            output = result.strip()
            logger.debug("adb output: %s", output[:200] if output else "(empty)")
            return output
        except subprocess.TimeoutExpired:
            raise EmulatorError(f"ADB timeout ({timeout}s): {cmd}")
        except subprocess.CalledProcessError as e:
            raise EmulatorError(f"ADB error (exit {e.returncode}): {e.output[:500]}")

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    @property
    def adb_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Подключается к эмулятору через ``adb connect``.

        Returns:
            True если устройство доступно.
        Raises:
            AdbConnectionError: если подключиться не удалось.
        """
        logger.info("Подключение к эмулятору %s:%d ...", self.host, self.adb_port)
        try:
            output = self._adb_global(f"connect {self.host}:{self.adb_port}")
            if "connected" not in output.lower() and "already connected" not in output.lower():
                raise AdbConnectionError(
                    f"adb connect не удался: {output}"
                )
            # Проверяем, что девайс в списке
            devices = self._adb_global("devices")
            if self.device_serial not in devices:
                raise AdbConnectionError(
                    f"Устройство {self.device_serial} не появилось в adb devices: {devices}"
                )
            self._connected = True
            logger.info("ADB подключён: %s", self.device_serial)
            return True
        except EmulatorError as e:
            raise AdbConnectionError(str(e))
        except FileNotFoundError:
            raise AdbConnectionError("adb не найдена в PATH. Установите android-platform-tools.")

    def _adb_global(self, args: str, timeout: int = 30) -> str:
        """Выполняет adb-команду без -s (для connect, devices и т.д.)."""
        cmd = f"adb {args}"
        logger.debug("adb (global): %s", cmd)
        try:
            result = subprocess.check_output(
                cmd, shell=True, text=True, timeout=timeout,
                stderr=subprocess.STDOUT,
            )
            return result.strip()
        except subprocess.TimeoutExpired:
            raise EmulatorError(f"ADB global timeout ({timeout}s): {cmd}")
        except subprocess.CalledProcessError as e:
            raise EmulatorError(f"ADB global error (exit {e.returncode}): {e.output[:500]}")

    def wait_for_boot(self, timeout: int = 120) -> bool:
        """Ждёт полной загрузки устройства (boot_completed == 1)."""
        logger.info("Ожидание загрузки устройства (timeout %ds)...", timeout)
        start = time.time()
        while time.time() - start < timeout:
            try:
                output = self._adb("shell getprop sys.boot_completed", timeout=10)
                if output.strip() == "1":
                    logger.info("Устройство загружено")
                    return True
            except EmulatorError:
                pass
            time.sleep(3)
        raise DeviceNotReadyError(
            f"Устройство не загрузилось за {timeout}с"
        )

    def install_apk(self, apk_path: Path) -> bool:
        """Устанавливает APK на устройство через ADB (не через docker cp)."""
        if not self._connected:
            self.connect()
        logger.info("Установка APK: %s", apk_path.name)
        try:
            output = self._adb(f"install -r {apk_path}", timeout=120)
            if "success" in output.lower():
                logger.info("APK установлен: %s", apk_path.name)
                return True
            raise ApkInstallError(f"install вернул: {output}")
        except EmulatorError as e:
            raise ApkInstallError(f"Ошибка установки {apk_path.name}: {e}")

    def start_app(self, package_name: str) -> bool:
        """Запускает приложение через monkey (один event)."""
        try:
            self._adb(f"shell monkey -p {package_name} 1", timeout=15)
            logger.info("Приложение запущено: %s", package_name)
            return True
        except EmulatorError as e:
            raise EmulatorError(f"Не удалось запустить {package_name}: {e}")

    def stop_app(self, package_name: str) -> None:
        """Останавливает приложение."""
        try:
            self._adb(f"shell am force-stop {package_name}", timeout=10)
        except EmulatorError:
            logger.warning("Не удалось остановить %s", package_name)

    def ensure_frida_server(self) -> bool:
        """Проверяет, что frida-server доступен на устройстве."""
        # Фактическую проверку делает FridaManager через python-биндинги,
        # здесь — поверхностная проверка через adb shell
        try:
            self._adb("shell pidof frida-server", timeout=5)
            logger.info("frida-server запущен на устройстве")
            return True
        except EmulatorError:
            logger.warning("frida-server не найден на устройстве")
            return False

    def clear_logcat(self) -> None:
        """Очищает logcat."""
        try:
            self._adb("logcat -c", timeout=5)
        except EmulatorError:
            pass

    def get_logcat(self, lines: int = 300) -> str:
        """Получает последние записи logcat."""
        try:
            return self._adb(f"logcat -d -t {lines}", timeout=10)
        except EmulatorError:
            return ""

    def take_screenshot(self, output_path: str) -> bool:
        """Делает скриншот."""
        try:
            self._adb(f"exec-out screencap -p > {output_path}", timeout=15)
            return True
        except EmulatorError:
            return False

    # ------------------------------------------------------------------
    # Input-методы (для будущих UI-сценариев, не вызываются из оркестратора)
    # ------------------------------------------------------------------

    def input_text(self, text: str) -> None:
        self._adb(f'shell input text "{text}"')

    def tap(self, x: int, y: int) -> None:
        self._adb(f"shell input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 200) -> None:
        self._adb(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")

"""Управление Frida через python-биндинги.

Упрощённый вариант: приложение запускается через adb, затем Frida
аттачится к уже запущенному процессу. Надёжнее и проще spawn.
import frida — ленивый, модуль импортируется без установленной frida.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Исключения
# ---------------------------------------------------------------------------

class FridaError(Exception):
    """Базовое исключение модуля Frida."""


class FridaUnavailableError(FridaError):
    """Библиотека frida не установлена."""


class FridaServerNotReachable(FridaError):
    """frida-server на устройстве не отвечает."""


class ProcessAttachError(FridaError):
    """Не удалось attach к процессу."""


# ---------------------------------------------------------------------------
# FridaManager
# ---------------------------------------------------------------------------

class FridaManager:
    """Управление Frida-хуками через python API."""

    def __init__(self, host: Optional[str] = None, port: int = 27042):
        self.host = host or os.getenv("EMULATOR_HOST", "android-emulator")
        self.port = port
        self._device = None
        self._session = None
        self._script = None
        self._messages: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Ленивый import frida
    # ------------------------------------------------------------------

    @staticmethod
    def _import_frida():
        try:
            import frida
            logger.debug("frida импортирована, версия: %s", frida.__version__)
            return frida
        except ImportError:
            raise FridaUnavailableError(
                "Модуль frida не установлен. pip install frida==17.15.4"
            )

    # ------------------------------------------------------------------
    # Подключение к remote frida-server
    # ------------------------------------------------------------------

    def connect(self) -> Any:
        """Подключается к remote frida-server.

        Returns:
            frida.Device
        Raises:
            FridaUnavailableError / FridaServerNotReachable
        """
        frida_mod = self._import_frida()
        try:
            mgr = frida_mod.get_device_manager()
            addr = f"{self.host}:{self.port}"
            logger.info("Подключение к frida-server: %s", addr)
            device = mgr.add_remote_device(addr)
            _ = device.enumerate_processes()
            self._device = device
            logger.info("Frida подключена к %s", addr)
            return device
        except frida_mod.TransportError as e:
            raise FridaServerNotReachable(
                f"frida-server на {self.host}:{self.port} не отвечает: {e}"
            )
        except Exception as e:
            raise FridaServerNotReachable(f"Ошибка подключения к frida: {e}")

    # ------------------------------------------------------------------
    # Attach к запущенному процессу (упрощённый путь)
    # ------------------------------------------------------------------

    def attach(self, package: str, script_source: str,
               on_message: Optional[Callable] = None) -> tuple:
        """Attach к запущенному процессу по имени пакета.

        Приложение должно быть уже запущено через adb.
        Frida находит PID и аттачится с хуками.

        Args:
            package: имя пакета (например com.example.app).
            script_source: JS-код хуков.
            on_message: callback для сообщений (по умолчанию — self._handle_message).

        Returns:
            (session, script)
        Raises:
            ProcessAttachError
        """
        frida_mod = self._import_frida()
        self._messages = []

        if not self._device:
            self.connect()

        device = self._device

        # Найти PID по имени пакета
        try:
            pid = self._find_pid(device, package)
            if pid is None:
                raise ProcessAttachError(
                    f"Процесс {package} не найден. Запустите приложение через adb."
                )
            logger.info("Attach к PID %d (%s)", pid, package)
        except FridaError:
            raise
        except Exception as e:
            raise ProcessAttachError(f"Ошибка поиска PID {package}: {e}")

        # Attach
        try:
            session = device.attach(pid)
            self._session = session
        except Exception as e:
            raise ProcessAttachError(f"Не удалось attach к PID {pid}: {e}")

        # Create script
        def _default_handler(message, data):
            self._handle_message(message, data)

        handler = on_message or _default_handler

        try:
            script = session.create_script(script_source)
            script.on("message", handler)
            script.load()
            self._script = script
            logger.info("Frida-скрипт загружен, хуки установлены")
        except Exception as e:
            raise ProcessAttachError(f"Не удалось загрузить скрипт: {e}")

        return session, script

    # ------------------------------------------------------------------
    # Поиск PID
    # ------------------------------------------------------------------

    def _find_pid(self, device, package: str) -> Optional[int]:
        """Ищет PID процесса по имени пакета среди процессов устройства."""
        for i in range(5):
            try:
                for proc in device.enumerate_processes():
                    if proc.name == package:
                        logger.info("Найден PID %d для %s", proc.pid, package)
                        return proc.pid
            except Exception as e:
                logger.debug("enumer_processes attempt %d: %s", i, e)
            time.sleep(1)
        return None

    # ------------------------------------------------------------------
    # Обработка сообщений
    # ------------------------------------------------------------------

    def _handle_message(self, message: dict, data: bytes) -> None:
        if message.get("type") == "send":
            try:
                payload = message.get("payload")
                if isinstance(payload, dict):
                    self._messages.append(payload)
                    logger.debug(
                        "Frida: %s = %s",
                        payload.get("identifier_id"),
                        str(payload.get("value", ""))[:60],
                    )
            except Exception as e:
                logger.warning("Ошибка парсинга payload: %s", e)
        elif message.get("type") == "error":
            logger.warning("Frida error: %s", message.get("description", "")[:200])

    def get_messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    # ------------------------------------------------------------------
    # Очистка
    # ------------------------------------------------------------------

    def disconnect(self) -> None:
        try:
            if self._script:
                self._script.unload()
        except Exception:
            pass
        try:
            if self._session:
                self._session.detach()
        except Exception:
            pass

        self._device = None
        self._session = None
        self._script = None
        self._messages = []
        logger.info("Frida: отключение завершено")

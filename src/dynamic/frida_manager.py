"""Управление Frida через python-биндинги (не subprocess+grep).

- ``import frida`` выполняется **лениво** внутри методов, чтобы модуль
  импортировался без установленной frida (важно для тестов статики и
  импорта в ``main.py``).
- Подключение к remote device (``frida.get_device_manager().add_remote_device``).
- Spawn + attach **до** resume — ранние вызовы не теряются.
"""

from __future__ import annotations

import json
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
    """Не удалось spawn/attach к процессу."""


# ---------------------------------------------------------------------------
# FridaManager
# ---------------------------------------------------------------------------

class FridaManager:
    """Управление Frida-хуками через python API."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 27042,
    ):
        self.host = host or os.getenv("EMULATOR_HOST", "android-emulator")
        self.port = port
        self._device = None
        self._session = None
        self._script = None
        self._pid = None
        self._messages: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Ленивый import frida
    # ------------------------------------------------------------------

    @staticmethod
    def _import_frida():
        """Ленивый импорт — не требует frida при import модуля."""
        try:
            import frida
            logger.debug("frida импортирована, версия: %s", frida.__version__)
            return frida
        except ImportError:
            raise FridaUnavailableError(
                "Модуль frida не установлен. pip install frida==17.15.4"
            )

    # ------------------------------------------------------------------
    # Подключение
    # ------------------------------------------------------------------

    def connect(self) -> Any:
        """Подключается к remote frida-server.

        Returns:
            frida.Device — объект подключённого устройства.
        Raises:
            FridaUnavailableError: frida не установлена.
            FridaServerNotReachable: frida-server не отвечает.
        """
        frida_mod = self._import_frida()

        try:
            mgr = frida_mod.get_device_manager()
            addr = f"{self.host}:{self.port}"
            logger.info("Подключение к frida-server: %s", addr)
            device = mgr.add_remote_device(addr)
            # Проверяем, что устройство отвечает
            _ = device.enumerate_processes()
            self._device = device
            logger.info("Frida подключена к %s", addr)
            return device
        except frida_mod.TransportError as e:
            raise FridaServerNotReachable(
                f"frida-server на {self.host}:{self.port} не отвечает: {e}"
            )
        except Exception as e:
            raise FridaServerNotReachable(
                f"Ошибка подключения к frida: {e}"
            )

    # ------------------------------------------------------------------
    # Spawn + Attach (Frida прикрепляется ДО старта приложения)
    # ------------------------------------------------------------------

    def spawn_and_attach(
        self,
        package: str,
        script_source: str,
        on_message: Optional[Callable] = None,
    ) -> tuple:
        """Spawn процесса, attach скрипта, return (session, script, pid).

        Приложение после spawn остаётся **в состоянии suspended** — caller
        должен вызвать ``device.resume(pid)`` после настройки.

        Args:
            package: имя пакета приложения.
            script_source: JS-код хуков.
            on_message: callback для сообщений скрипта (по умолчанию —
                        внутренний сбор в self._messages).

        Returns:
            (session, script, pid)
        Raises:
            ProcessAttachError: не удалось spawn/attach.
        """
        frida_mod = self._import_frida()
        self._messages = []

        if not self._device:
            self.connect()

        device = self._device

        # 1. Spawn
        try:
            logger.info("Spawn: %s", package)
            pid = device.spawn([package])
            self._pid = pid
            logger.info("PID: %d", pid)
        except Exception as e:
            raise ProcessAttachError(f"Не удалось spawn {package}: {e}")

        # 2. Attach
        try:
            logger.info("Attach к PID %d", pid)
            session = device.attach(pid)
            self._session = session
        except Exception as e:
            raise ProcessAttachError(f"Не удалось attach к PID {pid}: {e}")

        # 3. Create script
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

        return session, script, pid

    def resume(self, pid: Optional[int] = None) -> None:
        """Resume spawn'нутого процесса (приложение начинает работу)."""
        if not self._device:
            return
        target_pid = pid or self._pid
        if target_pid:
            try:
                self._device.resume(target_pid)
                logger.info("Process resumed: PID %d", target_pid)
            except Exception as e:
                logger.error("Не удалось resume PID %d: %s", target_pid, e)

    # ------------------------------------------------------------------
    # Сбор сообщений
    # ------------------------------------------------------------------

    def _handle_message(self, message: dict, data: bytes) -> None:
        """Обработчик сообщений от Frida-скрипта."""
        if message.get("type") == "send":
            try:
                payload = message.get("payload")
                if isinstance(payload, dict):
                    self._messages.append(payload)
                    logger.debug(
                        "Frida message: %s = %s",
                        payload.get("identifier_id"),
                        str(payload.get("value", ""))[:60],
                    )
            except Exception as e:
                logger.warning("Ошибка парсинга payload: %s", e)
        elif message.get("type") == "error":
            logger.warning("Frida script error: %s", message.get("description", "")[:200])
        else:
            logger.debug("Frida message (type=%s): %s",
                         message.get("type"), str(message)[:200])

    def get_messages(self) -> list[dict[str, Any]]:
        """Возвращает накопленные сообщения."""
        return list(self._messages)

    def collect(self, timeout: float = 60.0) -> list[dict[str, Any]]:
        """Собирает сообщения в течение timeout, затем возвращает."""
        self._messages = []
        time.sleep(timeout)
        return self.get_messages()

    # ------------------------------------------------------------------
    # Очистка
    # ------------------------------------------------------------------

    def disconnect(self) -> None:
        """Корректная очистка session/script."""
        try:
            if self._script:
                self._script.unload()
                self._script = None
        except Exception as e:
            logger.debug("Ошибка unload скрипта: %s", e)

        try:
            if self._session:
                self._session.detach()
                self._session = None
        except Exception as e:
            logger.debug("Ошибка detach: %s", e)

        try:
            if self._pid and self._device:
                try:
                    self._device.kill(self._pid)
                except Exception:
                    pass
        except Exception:
            pass

        self._device = None
        self._pid = None
        self._messages = []
        logger.info("Frida: отключение завершено")

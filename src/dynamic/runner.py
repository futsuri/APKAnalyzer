"""Универсальный прогонщик приложения (не завязан на конкретный APK).

Интерфейс ``AppRunner`` заменяемый — позже тестировщик подключает свой
``ScriptedScenario`` impl. По умолчанию используется ``MonkeyRunner``
(adb shell monkey).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .emulator_controller import EmulatorController

logger = logging.getLogger(__name__)


class AppRunner(ABC):
    """Базовый интерфейс прогонщика приложения."""

    @abstractmethod
    def run(self, emulator: EmulatorController, package: str) -> None:
        """Запускает взаимодействие с приложением.

        Args:
            emulator: контроллер эмулятора для отправки команд.
            package: имя пакета приложения.
        """
        ...


class MonkeyRunner(AppRunner):
    """Универсальный прогон через ``adb shell monkey``.

    Не завязан на конкретное приложение — генерирует случайные события
    UI (тапы, свайпы, ввод и т.д.).
    """

    def __init__(
        self,
        events: int = 500,
        seed: int = 42,
        throttle: int = 100,
        pct_touch: int = 40,
        pct_motion: int = 20,
        pct_appswitch: int = 5,
        pct_nav: int = 15,
        pct_major_nav: int = 5,
        pct_syskeys: int = 5,
    ):
        self.events = events
        self.seed = seed
        self.throttle = throttle
        self.pct_touch = pct_touch
        self.pct_motion = pct_motion
        self.pct_appswitch = pct_appswitch
        self.pct_nav = pct_nav
        self.pct_major_nav = pct_major_nav
        self.pct_syskeys = pct_syskeys

    def run(self, emulator: EmulatorController, package: str) -> None:
        """Запускает monkey-прогон приложения."""
        logger.info(
            "MonkeyRunner: package=%s, events=%d, seed=%d, throttle=%dms",
            package, self.events, self.seed, self.throttle,
        )
        try:
            cmd = (
                f"shell monkey -p {package} "
                f"-v "
                f"--pct-touch {self.pct_touch} "
                f"--pct-motion {self.pct_motion} "
                f"--pct-appswitch {self.pct_appswitch} "
                f"--pct-nav {self.pct_nav} "
                f"--pct-majornav {self.pct_major_nav} "
                f"--pct-syskeys {self.pct_syskeys} "
                f"--throttle {self.throttle} "
                f"-s {self.seed} "
                f"{self.events}"
            )
            output = emulator._adb(cmd, timeout=self.events * self.throttle // 1000 + 30)
            logger.info("MonkeyRunner завершён, вывод: %s", output[:300] if output else "(empty)")
        except Exception as e:
            # Monkey-прогон — best-effort, не должен ломать pipeline
            logger.warning("MonkeyRunner завершился с ошибкой (non-fatal): %s", e)

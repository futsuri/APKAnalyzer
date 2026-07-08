import subprocess
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class EmulatorController:
    """Управление эмулятором через docker exec"""

    def __init__(self, container_name: str = "android-emulator"):
        self.container_name = container_name
        self.adb_connected = False

    def _adb_cmd(self, args: str) -> str:
        """Выполняет ADB-команду через docker exec"""
        cmd = f'docker exec {self.container_name} adb {args}'
        logger.debug(f"Выполнение: {cmd}")
        try:
            result = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
            return result.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка ADB: {e.output}")
            return ""

    def connect(self) -> bool:
        """Проверяет, что эмулятор доступен"""
        logger.info(f"🔌 Проверка эмулятора {self.container_name}")
        try:
            devices = self._adb_cmd("devices")
            if "emulator-5554" in devices and "device" in devices:
                self.adb_connected = True
                logger.info("✅ Эмулятор готов")
                return True
            else:
                logger.warning("⚠️ Эмулятор не найден или не готов")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            return False

    def install_apk(self, apk_path: Path) -> bool:
        """Устанавливает APK на устройство"""
        if not self.adb_connected:
            self.connect()

        logger.info(f"📲 Установка APK: {apk_path.name}")
        try:
            # Копируем APK в контейнер
            copy_cmd = f"docker cp {apk_path} {self.container_name}:/tmp/{apk_path.name}"
            subprocess.check_call(copy_cmd, shell=True)

            # Устанавливаем APK
            self._adb_cmd(f"install -r /tmp/{apk_path.name}")
            logger.info("✅ APK установлен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка установки: {e}")
            return False

    def start_app(self, package_name: str) -> bool:
        """Запускает приложение"""
        logger.info(f"▶️ Запуск {package_name}")
        try:
            self._adb_cmd(f"shell monkey -p {package_name} 1")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            return False

    def stop_app(self, package_name: str) -> bool:
        """Останавливает приложение"""
        try:
            self._adb_cmd(f"shell am force-stop {package_name}")
            return True
        except:
            return False

    def input_text(self, text: str):
        """Вводит текст"""
        self._adb_cmd(f'shell input text "{text}"')

    def tap(self, x: int, y: int):
        """Нажатие на экран"""
        self._adb_cmd(f"shell input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 200):
        """Свайп"""
        self._adb_cmd(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")

    def get_logcat(self, lines: int = 300) -> str:
        """Получает логи logcat"""
        return self._adb_cmd(f"logcat -d -t {lines}")

    def clear_logcat(self):
        """Очищает логи"""
        self._adb_cmd("logcat -c")

    def take_screenshot(self, output_path: str) -> bool:
        """Делает скриншот"""
        try:
            cmd = f"docker exec {self.container_name} adb exec-out screencap -p > {output_path}"
            subprocess.check_call(cmd, shell=True)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка скриншота: {e}")
            return False
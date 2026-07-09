import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .emulator_controller import EmulatorController
from .frida_manager import FridaManager

logger = logging.getLogger(__name__)


class DynamicOrchestrator:
    """Главный оркестратор динамического анализа"""

    def __init__(self, container_name: str = "android-emulator"):
        logger.info("🔧 Инициализация DynamicOrchestrator")
        self.emulator = EmulatorController(container_name)
        self.frida = FridaManager()
        self.results = {
            "timestamp": None,
            "apk": None,
            "package": None,
            "identifiers": [],
            "logcat": [],
            "errors": []
        }
        logger.info(f"📱 Используется контейнер: {container_name}")

    def run_analysis(self, apk_path: Path, package_name: str) -> Dict:
        """Запускает полный динамический анализ"""
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК ДИНАМИЧЕСКОГО АНАЛИЗА")
        logger.info(f"📱 APK: {apk_path}")
        logger.info(f"📦 Package: {package_name}")
        logger.info("=" * 60)

        self.results["timestamp"] = datetime.now().isoformat()
        self.results["apk"] = str(apk_path)
        self.results["package"] = package_name

        try:
            # 1. Подключение к эмулятору
            if not self.emulator.connect():
                self.results["errors"].append("Не удалось подключиться к эмулятору")
                return self.results

            # 2. Проверка готовности устройства
            if not self._wait_for_device():
                self.results["errors"].append("Устройство не готово")
                return self.results

            # 3. Очистка логов
            self.emulator.clear_logcat()

            # 4. Установка APK
            if not self.emulator.install_apk(apk_path):
                self.results["errors"].append("Не удалось установить APK")
                return self.results

            # 5. Запуск приложения
            if not self.emulator.start_app(package_name):
                self.results["errors"].append("Не удалось запустить приложение")
                return self.results

            # 6. Ожидание загрузки приложения
            time.sleep(5)

            # 7. Запуск Frida
            script_path = Path(__file__).parent / "scripts" / "hook_identifiers.js"
            if script_path.exists():
                frida_results = self.frida.run_hook(package_name, script_path, timeout=60)
                self.results["identifiers"] = frida_results
                logger.info(f"✅ Найдено {len(frida_results)} идентификаторов")
            else:
                logger.warning(f"⚠️ Frida скрипт не найден: {script_path}")

            # 8. Сбор логов
            logcat = self.emulator.get_logcat(lines=300)
            self.results["logcat"] = logcat.split('\n')

            # 9. Закрытие приложения
            self.emulator.stop_app(package_name)

            # 10. Отключение
            self.emulator.adb_connected = False

            logger.info("=" * 60)
            logger.info(f"✅ АНАЛИЗ ЗАВЕРШЁН. Найдено: {len(self.results['identifiers'])}")
            logger.info("=" * 60)

            return self.results

        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            self.results["errors"].append(str(e))
            return self.results

    def _wait_for_device(self, timeout: int = 60) -> bool:
        """Ожидает готовности устройства"""
        logger.info(f"⏳ Ожидание устройства (таймаут {timeout}с)...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                # Проверяем, что устройство готово через docker exec
                import subprocess
                cmd = f'docker exec {self.emulator.container_name} adb shell getprop sys.boot_completed'
                result = subprocess.check_output(cmd, shell=True, text=True)
                if result.strip() == "1":
                    logger.info("✅ Устройство готово")
                    return True
            except Exception as e:
                logger.debug(f"   Ожидание... {str(e)[:50]}")
            time.sleep(2)
        logger.error("❌ Таймаут ожидания устройства")
        return False

    def save_results(self, output_dir: Path) -> Path:
        """Сохраняет результаты в JSON"""
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"dynamic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str, ensure_ascii=False)

        logger.info(f"💾 Результаты сохранены: {filepath}")
        return filepath

    def generate_summary(self) -> Dict:
        """Генерирует краткую сводку по результатам"""
        return {
            "total_identifiers": len(self.results["identifiers"]),
            "identifier_types": list(set([i["type"] for i in self.results["identifiers"]])),
            "errors": self.results["errors"],
            "apk": self.results["apk"],
            "package": self.results["package"],
            "timestamp": self.results["timestamp"]
        }

    def _run_automation_scenario(self, package_name: str):
        """Автоматизированный сценарий для Signal"""
        logger.info("🔄 Запуск автоматизации...")
        time.sleep(2)

        # Ввод номера телефона
        logger.info("📱 Ввод номера телефона...")
        self.emulator.tap(540, 800)
        time.sleep(1)
        self.emulator.input_text("+79998887766")
        time.sleep(1)
        self.emulator.tap(540, 1500)
        time.sleep(3)

        # Открытие меню
        logger.info("☰ Открытие меню...")
        self.emulator.tap(900, 100)
        time.sleep(1)

        # Настройки
        logger.info("⚙️ Открытие настроек...")
        self.emulator.tap(540, 400)
        time.sleep(2)
        self.emulator.swipe(540, 1200, 540, 500, 300)
        time.sleep(1)

        # Возврат
        self.emulator.tap(100, 100)
        time.sleep(1)

        logger.info("✅ Автоматизация завершена")
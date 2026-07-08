import subprocess
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class FridaManager:
    """Управление Frida-хуками"""

    def __init__(self):
        logger.info("🔧 Инициализация FridaManager")
        self.frida_version = self._get_frida_version()
        self.device_serial = "emulator-5554"
        logger.info(f"📱 Используется устройство: {self.device_serial}")

    def _get_frida_version(self) -> Optional[str]:
        """Проверяет, что Frida установлена"""
        logger.info("🔍 Проверка версии Frida...")
        try:
            output = subprocess.check_output("frida --version", shell=True, text=True)
            logger.info(f"✅ Frida версия: {output.strip()}")
            return output.strip()
        except Exception as e:
            logger.error(f"❌ Frida не найдена: {e}")
            logger.error("   Установите: pip install frida-tools")
            return None

    def _check_frida_server(self) -> bool:
        """Проверяет, что Frida Server работает на устройстве"""
        logger.info("🔍 Проверка Frida Server на устройстве...")
        try:
            # Проверяем через frida-ps
            output = subprocess.check_output("frida-ps -U", shell=True, text=True, timeout=5)
            logger.info(f"✅ Frida Server работает, найдено процессов: {len(output.splitlines())}")
            return True
        except subprocess.TimeoutExpired:
            logger.error("❌ Таймаут при проверке Frida Server")
            return False
        except Exception as e:
            logger.error(f"❌ Frida Server не отвечает: {e}")
            logger.info("   Запустите Frida Server на эмуляторе:")
            logger.info("   adb shell /data/local/tmp/frida-server &")
            return False

    def _get_process_pid(self, package_name: str) -> Optional[int]:
        """Находит PID процесса по имени пакета"""
        logger.info(f"🔍 Поиск PID для {package_name}...")
        try:
            cmd = f"adb -s {self.device_serial} shell ps"
            logger.debug(f"   Команда: {cmd}")
            output = subprocess.check_output(cmd, shell=True, text=True)
            logger.debug(f"   Получено {len(output.splitlines())} строк")
            
            for line in output.split('\n'):
                if package_name in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = int(parts[1])
                        logger.info(f"✅ Найден PID {pid} для {package_name}")
                        logger.debug(f"   Строка: {line}")
                        return pid
            logger.warning(f"⚠️ Процесс {package_name} не найден в выводе ps")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка поиска PID: {e}")
            return None

    def run_hook(self, package_name: str, script_path: Path, timeout: int = 60) -> List[Dict]:
        """Запускает Frida-скрипт на приложении"""
        logger.info("=" * 50)
        logger.info("🎣 ЗАПУСК FRIDA")
        logger.info(f"📦 Package: {package_name}")
        logger.info(f"📜 Script: {script_path}")
        logger.info("=" * 50)

        # Проверка 1: Frida установлена
        if not self.frida_version:
            logger.error("❌ Frida не установлена")
            return []

        # Проверка 2: Frida Server работает
        if not self._check_frida_server():
            logger.error("❌ Frida Server не работает")
            return []

        # Проверка 3: Запуск приложения через ADB
        logger.info(f"📱 Запуск приложения {package_name} через ADB...")
        try:
            cmd = f"adb -s {self.device_serial} shell monkey -p {package_name} 1"
            logger.debug(f"   Команда: {cmd}")
            output = subprocess.check_output(cmd, shell=True, text=True)
            logger.info(f"✅ Приложение запущено")
            logger.debug(f"   Вывод: {output}")
            time.sleep(5)
        except Exception as e:
            logger.error(f"❌ Не удалось запустить приложение: {e}")
            return []

        # Проверка 4: Поиск PID
        pid = self._get_process_pid(package_name)
        if not pid:
            logger.error(f"❌ Процесс {package_name} не найден")
            logger.info("   Проверьте, что приложение действительно запущено:")
            logger.info(f"   adb -s {self.device_serial} shell ps | grep {package_name}")
            return []

        # Проверка 5: Проверка скрипта
        if not script_path.exists():
            logger.error(f"❌ Frida скрипт не найден: {script_path}")
            return []

        # Проверка 6: Запуск Frida
        logger.info(f"🔗 Подключение к PID: {pid}")
        cmd = [
            "frida", "-U",
            "-p", str(pid),
            "-l", str(script_path),
            "--no-pause"
        ]
        logger.debug(f"   Команда: {' '.join(cmd)}")
        
        try:
            logger.info("⏳ Ожидание вывода Frida...")
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout, text=True)
            logger.info(f"✅ Frida завершилась, получено {len(output)} символов")
            
            # Проверка: есть ли хуки в выводе
            if "[*] Frida hooks started" in output:
                logger.info("✅ Хуки успешно установлены")
            else:
                logger.warning("⚠️ Хуки не были установлены (возможно, скрипт не выполнился)")
            
            # Проверка: есть ли найденные идентификаторы
            identifiers = self._parse_frida_output(output)
            if identifiers:
                logger.info(f"✅ Найдено {len(identifiers)} идентификаторов")
                for i in identifiers[:3]:
                    logger.info(f"   - {i['type']}: {i['value'][:50]}")
            else:
                logger.warning("⚠️ Идентификаторы не найдены")
                logger.info("   Возможно, приложение не вызывало API во время анализа")
            
            return identifiers
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ Frida превысила время ожидания ({timeout}с)")
            logger.info("   Попробуйте увеличить таймаут или выполнить действия вручную")
            return []
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Ошибка Frida (код {e.returncode})")
            if e.output:
                logger.error(f"   Вывод: {e.output[:500]}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка Frida: {e}")
            return []

    def _parse_frida_output(self, output: str) -> List[Dict]:
        """Парсит вывод Frida в структурированный формат"""
        logger.info("🔍 Парсинг вывода Frida...")
        identifiers = []
        id_types = ["IMEI", "ANDROID_ID", "MAC", "IMSI", "SERIAL", "PHONE", "FINGERPRINT"]

        lines = output.split('\n')
        logger.debug(f"   Всего строк: {len(lines)}")
        
        for line in lines:
            for id_type in id_types:
                if id_type in line and ']' in line:
                    parts = line.split(']', 1)
                    if len(parts) > 1:
                        value = parts[1].strip()
                        if value and value != "null" and value != "undefined":
                            identifiers.append({
                                "type": id_type,
                                "value": value,
                                "source": "Frida Hook",
                                "timestamp": time.time()
                            })
                            logger.debug(f"   Найден {id_type}: {value}")
        
        logger.info(f"✅ Найдено {len(identifiers)} идентификаторов в выводе")
        return identifiers
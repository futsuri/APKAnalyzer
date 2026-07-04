import logging
import subprocess
import shutil
import tempfile
from pathlib import Path

from src.core.config import APKTOOL_PATH, JADX_PATH, TIMEOUT, MAX_LIBRARIES
from src.static.parsers.manifest_parser import ManifestParser
from src.static.detectors.identifier_detector import IdentifierDetector
from src.static.detectors.secret_detector import SecretDetector  

logger = logging.getLogger(__name__)


class ApkService:
    def __init__(self, apk_path: Path):
        self.apk_path = apk_path
        self.temp_dir = None

    def analyze_simple(self):
        logger.info(f"Начинаем анализ APK: {self.apk_path}")

        result = {
            'apk_file': self.apk_path.name,
            'manifest': None,
            'identifiers': {},
            'secrets': [],
            'libraries': []
        }

        try:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="apk_analysis_"))
            logger.info(f"Создана временная директория: {self.temp_dir}")

            self._run_apktool()
            source_dir = self._run_jadx()

            manifest_path = self.temp_dir / "apktool" / "AndroidManifest.xml"
            if manifest_path.exists():
                manifest_parser = ManifestParser(manifest_path)
                manifest_data = manifest_parser.parse()
                result['manifest'] = manifest_data
                logger.info(f"Манифест обработан: {manifest_data.get('package', 'unknown')}")

            if source_dir and source_dir.exists():
                identifier_detector = IdentifierDetector(source_dir)
                result['identifiers'] = identifier_detector.scan()
                logger.info("Поиск идентификаторов завершён")

                secret_detector = SecretDetector(source_dir)  # Исправлено!
                result['secrets'] = secret_detector.scan()    # Исправлено!
                logger.info(f"Найдено секретов: {len(result['secrets'])}")

                result['libraries'] = self._collect_libraries(source_dir)

        except Exception as e:
            logger.error(f"Ошибка при анализе APK: {e}")
            raise

        return result

    def _run_apktool(self):
        output_dir = self.temp_dir / "apktool"
        cmd = f"{APKTOOL_PATH} d {self.apk_path} -o {output_dir} -f"
        logger.info(f"Запуск: {cmd}")

        try:
            # Запускаем без захвата вывода, чтобы не было проблем с кодировкой
            result = subprocess.run(cmd, shell=True, timeout=TIMEOUT)
            if result.returncode != 0:
                logger.warning(f"apktool завершился с кодом {result.returncode}")
            else:
                logger.info("apktool выполнен успешно")
        except subprocess.TimeoutExpired:
            logger.error(f"apktool превысил время ожидания ({TIMEOUT}с)")
        except Exception as e:
            logger.error(f"Ошибка при запуске apktool: {e}")

    def _run_jadx(self) -> Path:
        output_dir = self.temp_dir / "jadx_output"
        cmd = f"{JADX_PATH} {self.apk_path} -d {output_dir} --show-bad-code"
        logger.info(f"Запуск: {cmd}")

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=TIMEOUT * 2)
            if result.returncode != 0:
                logger.warning(f"jadx предупреждение: {result.stderr}")
            else:
                logger.info("jadx выполнен успешно")
        except subprocess.TimeoutExpired:
            logger.error(f"jadx превысил время ожидания ({TIMEOUT * 2}с)")
        except Exception as e:
            logger.error(f"Ошибка при запуске jadx: {e}")

        return output_dir

    def _collect_libraries(self, source_dir: Path) -> list:
        libs = set()
        if not source_dir.exists():
            return []

        for path in source_dir.rglob("*.java"):
            if path.parent.name and not path.parent.name.startswith('.'):
                rel_path = path.relative_to(source_dir)
                parts = str(rel_path).split('/')
                if len(parts) >= 2:
                    pkg = '.'.join(parts[:2])
                    if not pkg.startswith(('android', 'java', 'javax', 'androidx')):
                        libs.add(pkg)

        return sorted(list(libs))[:MAX_LIBRARIES]

    def cleanup(self):
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info(f"Временная директория удалена: {self.temp_dir}")
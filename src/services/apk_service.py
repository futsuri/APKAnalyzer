import logging
import subprocess
import shutil
import tempfile
from pathlib import Path

from src.core.config import APKTOOL_PATH, JADX_PATH, TIMEOUT, MAX_LIBRARIES
from src.static.parsers.manifest_parser import ManifestParser
from src.static.detectors.identifier_detector import IdentifierDetector
from src.static.detectors.secret_detector import SecretDetector
from src.models.analysis import AnalysisResult, Manifest, Permission, Component, Secret, Identifier

logger = logging.getLogger(__name__)


class ApkService:
    def __init__(self, apk_path: Path):
        self.apk_path = apk_path
        self.temp_dir = None

    def analyze_simple(self) -> AnalysisResult:
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

                secret_detector = SecretDetector(source_dir)
                result['secrets'] = secret_detector.scan()
                logger.info(f"Найдено секретов: {len(result['secrets'])}")

                result['libraries'] = self._collect_libraries(source_dir)

            # Преобразование в объекты моделей
            manifest_obj = None
            if result['manifest']:
                manifest_data = result['manifest']
                perms = [
                    Permission(p['name'], p['is_dangerous'], description=p.get('description'))
                    for p in manifest_data.get('permissions', [])
                ]
                activities = [Component(c['name'], c['exported'], 'activity') for c in manifest_data.get('activities', [])]
                services = [Component(c['name'], c['exported'], 'service') for c in manifest_data.get('services', [])]
                receivers = [Component(c['name'], c['exported'], 'receiver') for c in manifest_data.get('receivers', [])]
                providers = [Component(c['name'], c['exported'], 'provider') for c in manifest_data.get('providers', [])]
                
                manifest_obj = Manifest(
                    package=manifest_data.get('package', 'unknown'),
                    version_code=manifest_data.get('version_code', '0'),
                    version_name=manifest_data.get('version_name', 'unknown'),
                    min_sdk=manifest_data.get('min_sdk', 0),
                    target_sdk=manifest_data.get('target_sdk', 0),
                    permissions=perms,
                    activities=activities,
                    services=services,
                    receivers=receivers,
                    providers=providers
                )

            identifiers_obj = {}
            for name, data in result['identifiers'].items():
                identifiers_obj[name] = Identifier(
                    name=name,
                    found=data.get('found', False),
                    locations=data.get('locations', []),
                    risk_level=None
                )

            secrets_obj = []
            for s in result['secrets']:
                secrets_obj.append(Secret(
                    type=s.get('type'),
                    value=s.get('value'),
                    location=s.get('location'),
                    risk_level=None
                ))

            return AnalysisResult(
                apk_file=self.apk_path.name,
                manifest=manifest_obj,
                identifiers=identifiers_obj,
                secrets=secrets_obj,
                libraries=result['libraries']
            )

        except Exception as e:
            logger.error(f"Ошибка при анализе APK: {e}")
            raise

    def _run_apktool(self):
        output_dir = self.temp_dir / "apktool"
        cmd = f"{APKTOOL_PATH} d {self.apk_path} -o {output_dir} -f"
        logger.info(f"Запуск: {cmd}")

        try:
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
                parts = rel_path.parts
                if len(parts) >= 2:
                    pkg = '.'.join(parts[:2])
                    if not pkg.startswith(('android', 'java', 'javax', 'androidx')):
                        libs.add(pkg)

        return sorted(list(libs))[:MAX_LIBRARIES]

    def cleanup(self):
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info(f"Временная директория удалена: {self.temp_dir}")
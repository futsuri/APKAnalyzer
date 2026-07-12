import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from src.core.config import (
    APKTOOL_PATH,
    JADX_FALLBACK_TIMEOUT,
    JADX_PATH,
    JADX_PRIMARY_TIMEOUT,
    JADX_THREADS,
    MAX_LIBRARIES,
    TIMEOUT,
)
from src.models.analysis import AnalysisResult, Finding, Secret
from src.static.catalog import load_identifiers_catalog
from src.static.detectors.identifier_detector import IdentifierDetector
from src.static.detectors.secret_detector import SecretDetector
from src.static.parsers.manifest_parser import ManifestParser

logger = logging.getLogger(__name__)


class ApkService:
    def __init__(self, apk_path: Path):
        self.apk_path = apk_path
        self.temp_dir = None

    def analyze_simple(self) -> AnalysisResult:
        logger.info(f"Начинаем анализ APK: {self.apk_path}")
        result = AnalysisResult(apk_file=self.apk_path.name)
        catalog = load_identifiers_catalog()

        try:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="apk_analysis_"))
            logger.info(f"Создана временная директория: {self.temp_dir}")

            self._run_apktool()
            jadx_source_dir = self._run_jadx()
            apktool_dir = self.temp_dir / "apktool"

            manifest_path = apktool_dir / "AndroidManifest.xml"
            if manifest_path.exists():
                manifest_parser = ManifestParser(manifest_path)
                result.manifest = manifest_parser.parse()
                if result.manifest:
                    logger.info(f"Манифест обработан: {result.manifest.package}")

            manifest_permissions = []
            app_package = None
            if result.manifest:
                manifest_permissions = [permission.name for permission in result.manifest.permissions]
                app_package = result.manifest.package

            identifier_detector = IdentifierDetector(
                jadx_source_dir=jadx_source_dir if jadx_source_dir.exists() else None,
                apktool_dir=apktool_dir if apktool_dir.exists() else None,
                catalog=catalog,
                app_package=app_package,
                manifest_permissions=manifest_permissions,
            )
            result.identifiers = {
                identifier_id: Finding.from_dict(data)
                for identifier_id, data in identifier_detector.scan().items()
            }
            logger.info("Поиск идентификаторов завершён")

            if jadx_source_dir.exists():
                secret_detector = SecretDetector(jadx_source_dir)
                result.secrets = [Secret.from_dict(secret) for secret in secret_detector.scan()]
                logger.info(f"Найдено секретов: {len(result.secrets)}")
                result.libraries = self._collect_libraries(jadx_source_dir)
            elif apktool_dir.exists():
                secret_detector = SecretDetector(apktool_dir)
                result.secrets = [Secret.from_dict(secret) for secret in secret_detector.scan()]
                logger.info(f"Найдено секретов: {len(result.secrets)}")

        except Exception as error:
            logger.error(f"Ошибка при анализе APK: {error}")
            raise

        result.summary = {
            "apk_file": result.apk_file,
            "package": result.manifest.package if result.manifest else "unknown",
            "version": result.manifest.version_name if result.manifest else "unknown",
            "permissions_count": len(result.manifest.permissions) if result.manifest else 0,
            "identifiers_found": sum(1 for finding in result.identifiers.values() if finding.found),
            "identifiers_total": len(result.identifiers),
            "secrets_count": len(result.secrets),
            "libraries_count": len(result.libraries),
        }

        return result

    def _run_apktool(self):
        output_dir = self.temp_dir / "apktool"
        cmd = [APKTOOL_PATH, "d", str(self.apk_path), "-o", str(output_dir), "-f"]
        logger.info(f"Запуск: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, timeout=TIMEOUT)
            if result.returncode != 0:
                logger.warning(f"apktool завершился с кодом {result.returncode}")
            else:
                logger.info("apktool выполнен успешно")
        except subprocess.TimeoutExpired:
            logger.error(f"apktool превысил время ожидания ({TIMEOUT}с)")
        except Exception as error:
            logger.error(f"Ошибка при запуске apktool: {error}")

    def _run_jadx(self) -> Path:
        output_dir = self.temp_dir / "jadx_output"

        # Первая попытка: полная точность (--show-bad-code), но в несколько
        # потоков и с укороченным таймаутом. --show-bad-code иногда заставляет
        # jadx застревать на одном патологическом классе/методе (характерно
        # для крупных protobuf-приложений вроде Signal) — тогда однопоточный
        # прогон с большим таймаутом просто впустую ждёт весь лимит.
        primary_cmd = [
            JADX_PATH,
            str(self.apk_path),
            "-d",
            str(output_dir),
            "-j",
            str(JADX_THREADS),
            "--show-bad-code",
        ]
        if self._try_run_jadx(primary_cmd, JADX_PRIMARY_TIMEOUT, "основной"):
            return output_dir

        # Fallback: без --show-bad-code jadx намного быстрее сдаётся на
        # проблемном коде (просто помечает метод как нерасшифрованный вместо
        # попытки его дорисовать), поэтому вероятность повторного зависания
        # на том же месте существенно ниже. Выходную директорию чистим,
        # чтобы не смешивать частичный результат первой попытки со второй.
        shutil.rmtree(output_dir, ignore_errors=True)
        fallback_cmd = [
            JADX_PATH,
            str(self.apk_path),
            "-d",
            str(output_dir),
            "-j",
            str(JADX_THREADS),
        ]
        self._try_run_jadx(fallback_cmd, JADX_FALLBACK_TIMEOUT, "fallback (без --show-bad-code)")

        return output_dir

    def _try_run_jadx(self, cmd: list, timeout: int, label: str) -> bool:
        """Запускает jadx с заданными параметрами. Возвращает True при успехе."""
        logger.info(f"Запуск jadx ({label}, timeout={timeout}с): {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                logger.warning(f"jadx ({label}) предупреждение: {result.stderr}")
                return False
            logger.info(f"jadx ({label}) выполнен успешно")
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"jadx ({label}) превысил время ожидания ({timeout}с)")
            return False
        except Exception as error:
            logger.error(f"Ошибка при запуске jadx ({label}): {error}")
            return False

    def _collect_libraries(self, source_dir: Path) -> list:
        libs = set()
        if not source_dir.exists():
            return []

        for path in source_dir.rglob("*.java"):
            if path.parent.name and not path.parent.name.startswith("."):
                rel_path = path.relative_to(source_dir)
                parts = rel_path.parts
                if len(parts) >= 2:
                    pkg = ".".join(parts[:2])
                    if not pkg.startswith(("android", "java", "javax", "androidx")):
                        libs.add(pkg)

        return sorted(list(libs))[:MAX_LIBRARIES]

    def cleanup(self):
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info(f"Временная директория удалена: {self.temp_dir}")
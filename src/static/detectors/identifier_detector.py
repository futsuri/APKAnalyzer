import logging
from pathlib import Path

from src.core.config import IDENTIFIER_PATTERNS

logger = logging.getLogger(__name__)


class IdentifierDetector:
    def __init__(self, source_dir: Path):
        self.source_dir = source_dir
        self.results = {name: {'found': False, 'locations': []} for name in IDENTIFIER_PATTERNS}

    def scan(self):
        if not self.source_dir.exists():
            logger.error(f"Директория не найдена: {self.source_dir}")
            return self.results

        java_files = list(self.source_dir.rglob("*.java"))
        logger.info(f"Найдено {len(java_files)} Java файлов")

        for java_file in java_files:
            self._scan_file(java_file)

        for name in self.results:
            self.results[name]['found'] = bool(self.results[name]['locations'])

        return self.results

    def _scan_file(self, file_path: Path):
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return

        for identifier_name, patterns in IDENTIFIER_PATTERNS.items():
            for pattern in patterns:
                if pattern in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if pattern in line:
                            self.results[identifier_name]['locations'].append({
                                'file': str(file_path.relative_to(self.source_dir.parent)),
                                'line': i,
                                'code': line.strip()[:200]
                            })
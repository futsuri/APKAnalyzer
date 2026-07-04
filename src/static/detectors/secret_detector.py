import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SecretDetector:
    SECRET_PATTERNS = {
        "API_KEY": [
            r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,50})["\']?',
            r'AIza[0-9A-Za-z\-_]{35}',
        ],
        "TOKEN": [
            r'(?:token|access_token|auth_token)\s*[:=]\s*["\']?([a-zA-Z0-9\-_\.]{20,100})["\']?',
            r'Bearer\s+([a-zA-Z0-9\-_\.]{20,100})',
        ],
        "PASSWORD": [
            r'(?:password|passwd|pwd)\s*[:=]\s*["\']?([^\s"\']{6,})["\']?',
        ],
        "SECRET": [
            r'(?:secret|client_secret)\s*[:=]\s*["\']?([a-zA-Z0-9\-_]{20,50})["\']?',
        ],
        "PRIVATE_KEY": [
            r'-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----',
        ],
    }

    def __init__(self, source_dir: Path):
        self.source_dir = source_dir
        self.secrets = []

    def scan(self):
        if not self.source_dir.exists():
            return []

        java_files = list(self.source_dir.rglob("*.java"))
        logger.info(f"Сканирование {len(java_files)} файлов")

        for java_file in java_files:
            self._scan_file(java_file)

        return self.secrets

    def _scan_file(self, file_path: Path):
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for secret_type, patterns in self.SECRET_PATTERNS.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        value = match.group(1) if match.groups() else match.group(0)
                        if len(value) > 50:
                            value = value[:50] + "..."
                        self.secrets.append({
                            'type': secret_type,
                            'value': value,
                            'location': f"{file_path.relative_to(self.source_dir.parent)}:{i}"
                        })
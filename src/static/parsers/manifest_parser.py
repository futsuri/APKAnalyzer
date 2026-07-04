import logging
import xml.etree.ElementTree as ET
from pathlib import Path

# Исправленный импорт
from src.core.config import DANGEROUS_PERMISSIONS

logger = logging.getLogger(__name__)


class ManifestParser:
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path

    def parse(self):
        if not self.manifest_path.exists():
            logger.error(f"Манифест не найден: {self.manifest_path}")
            return {}

        try:
            tree = ET.parse(self.manifest_path)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.error(f"Ошибка парсинга манифеста: {e}")
            return {}

        manifest_data = {
            'package': root.get('package', 'unknown'),
            'version_code': root.get('android:versionCode', '0'),
            'version_name': root.get('android:versionName', 'unknown'),
            'min_sdk': 0,
            'target_sdk': 0,
            'permissions': [],
            'activities': [],
            'services': [],
            'receivers': [],
            'providers': []
        }

        uses_sdk = root.find('uses-sdk')
        if uses_sdk is not None:
            manifest_data['min_sdk'] = int(uses_sdk.get('android:minSdkVersion', '0') or '0')
            manifest_data['target_sdk'] = int(uses_sdk.get('android:targetSdkVersion', '0') or '0')

        for perm in root.findall('uses-permission'):
            name = perm.get('android:name', '')
            if name:
                manifest_data['permissions'].append({
                    'name': name,
                    'is_dangerous': name in DANGEROUS_PERMISSIONS,
                    'description': DANGEROUS_PERMISSIONS.get(name)
                })

        for tag in ['activity', 'service', 'receiver', 'provider']:
            for comp in root.findall(tag):
                name = comp.get('android:name', '')
                if name:
                    manifest_data[tag + 's'].append({
                        'name': name,
                        'exported': comp.get('android:exported', 'false') == 'true',
                        'type': tag
                    })

        return manifest_data
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

# Исправленный импорт
from src.core.config import DANGEROUS_PERMISSIONS

logger = logging.getLogger(__name__)

NS_ANDROID = "{http://schemas.android.com/apk/res/android}"


def get_android_attr(element, attr_name, default=''):
    val = element.get(f'{NS_ANDROID}{attr_name}')
    if val is None:
        val = element.get(f'android:{attr_name}')
    return val if val is not None else default


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
            'version_code': get_android_attr(root, 'versionCode', '0'),
            'version_name': get_android_attr(root, 'versionName', 'unknown'),
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
            min_sdk_str = get_android_attr(uses_sdk, 'minSdkVersion', '0')
            target_sdk_str = get_android_attr(uses_sdk, 'targetSdkVersion', '0')
            try:
                manifest_data['min_sdk'] = int(min_sdk_str)
            except ValueError:
                manifest_data['min_sdk'] = 0
            try:
                manifest_data['target_sdk'] = int(target_sdk_str)
            except ValueError:
                manifest_data['target_sdk'] = 0

        for perm in root.findall('uses-permission'):
            name = get_android_attr(perm, 'name', '')
            if name:
                manifest_data['permissions'].append({
                    'name': name,
                    'is_dangerous': name in DANGEROUS_PERMISSIONS,
                    'description': DANGEROUS_PERMISSIONS.get(name)
                })

        for tag in ['activity', 'service', 'receiver', 'provider']:
            for comp in root.findall(tag):
                name = get_android_attr(comp, 'name', '')
                if name:
                    exported_val = get_android_attr(comp, 'exported', 'false')
                    manifest_data[tag + 's'].append({
                        'name': name,
                        'exported': exported_val.lower() == 'true',
                        'type': tag
                    })

        return manifest_data
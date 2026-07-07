from enum import Enum


class RiskLevel(str, Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class Permission:
    def __init__(self, name, is_dangerous=False, risk_level=None, description=None):
        self.name = name
        self.is_dangerous = is_dangerous
        self.risk_level = risk_level or RiskLevel.LOW
        self.description = description

    def model_dump(self):
        return {
            'name': self.name,
            'is_dangerous': self.is_dangerous,
            'risk_level': self.risk_level.value if isinstance(self.risk_level, Enum) else self.risk_level,
            'description': self.description
        }


class Component:
    def __init__(self, name, exported=False, type='activity'):
        self.name = name
        self.exported = exported
        self.type = type

    def model_dump(self):
        return {
            'name': self.name,
            'exported': self.exported,
            'type': self.type
        }


class Secret:
    def __init__(self, type, value, location, risk_level=None):
        self.type = type
        self.value = value
        self.location = location
        self.risk_level = risk_level or RiskLevel.MEDIUM

    def model_dump(self):
        return {
            'type': self.type,
            'value': self.value,
            'location': self.location,
            'risk_level': self.risk_level.value if isinstance(self.risk_level, Enum) else self.risk_level
        }


class Identifier:
    def __init__(self, name, found=False, locations=None, risk_level=None):
        self.name = name
        self.found = found
        self.locations = locations or []
        self.risk_level = risk_level or RiskLevel.LOW

    def model_dump(self):
        return {
            'name': self.name,
            'found': self.found,
            'locations': self.locations,
            'risk_level': self.risk_level.value if isinstance(self.risk_level, Enum) else self.risk_level
        }


class Manifest:
    def __init__(self, package='unknown', version_code='0', version_name='unknown', min_sdk=0, target_sdk=0, permissions=None, activities=None, services=None, receivers=None, providers=None):
        self.package = package
        self.version_code = version_code
        self.version_name = version_name
        self.min_sdk = min_sdk
        self.target_sdk = target_sdk
        self.permissions = permissions or []
        self.activities = activities or []
        self.services = services or []
        self.receivers = receivers or []
        self.providers = providers or []

    def model_dump(self):
        return {
            'package': self.package,
            'version_code': self.version_code,
            'version_name': self.version_name,
            'min_sdk': self.min_sdk,
            'target_sdk': self.target_sdk,
            'permissions': [p.model_dump() for p in self.permissions],
            'activities': [c.model_dump() for c in self.activities],
            'services': [c.model_dump() for c in self.services],
            'receivers': [c.model_dump() for c in self.receivers],
            'providers': [c.model_dump() for c in self.providers]
        }


class AnalysisResult:
    def __init__(self, apk_file, manifest=None, identifiers=None, secrets=None, libraries=None, summary=True):
        self.apk_file = apk_file
        self.manifest = manifest
        self.identifiers = identifiers or {}
        self.secrets = secrets or []
        self.libraries = libraries or []
        self.summary = summary

    def model_dump(self):
        return {
            'apk_file': self.apk_file,
            'manifest': self.manifest.model_dump() if self.manifest else None,
            'identifiers': {k: v.model_dump() for k, v in self.identifiers.items()},
            'secrets': [s.model_dump() for s in self.secrets],
            'libraries': self.libraries,
            'summary': self.summary
        }

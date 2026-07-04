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


class Component:
    def __init__(self, name, exported=False, type='activity'):
        self.name = name
        self.exported = exported
        self.type = type


class Secret:
    def __init__(self, type, value, location, risk_level=None):
        self.type = type
        self.value = value
        self.location = location
        self.risk_level = risk_level or RiskLevel.MEDIUM


class Identifier:
    def __init__(self, name, found=False, locations=None, risk_level=None):
        self.name = name
        self.found = found
        self.locations = locations or []
        self.risk_level = risk_level or RiskLevel.LOW

from typing import List, Dict
from src.models.analysis import Permission, RiskLevel
from src.core.config import DANGEROUS_PERMISSIONS


class PermissionParser:
    """Анализ разрешений и их рисков"""

    @staticmethod
    def analyze_permissions(permissions: List[Permission]) -> Dict:
        """Анализирует разрешения и возвращает статистику"""
        dangerous = [p for p in permissions if p.is_dangerous]
        safe = [p for p in permissions if not p.is_dangerous]

        risk_counts = {
            RiskLevel.LOW: len([p for p in permissions if p.risk_level == RiskLevel.LOW]),
            RiskLevel.MEDIUM: len([p for p in permissions if p.risk_level == RiskLevel.MEDIUM]),
            RiskLevel.HIGH: len([p for p in permissions if p.risk_level == RiskLevel.HIGH]),
            RiskLevel.CRITICAL: len([p for p in permissions if p.risk_level == RiskLevel.CRITICAL]),
        }

        return {
            "total": len(permissions),
            "dangerous": len(dangerous),
            "safe": len(safe),
            "risk_counts": risk_counts,
            "dangerous_list": [p.name for p in dangerous],
            "risk_score": PermissionParser._calculate_risk_score(permissions)
        }

    @staticmethod
    def _calculate_risk_score(permissions: List[Permission]) -> int:
        """Расчёт общего риска (0-100)"""
        weights = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 3,
            RiskLevel.HIGH: 7,
            RiskLevel.CRITICAL: 10
        }

        score = 0
        for p in permissions:
            if p.risk_level in weights:
                score += weights[p.risk_level]

        # Нормализуем
        max_score = len(permissions) * 10
        if max_score > 0:
            return min(100, int((score / max_score) * 100))
        return 0
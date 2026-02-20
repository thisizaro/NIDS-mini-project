from abc import ABC, abstractmethod
from app.models.schemas import SeverityLevel, ModelFindingsAbnormal, Context
from app.config import Config


class SeverityStrategy(ABC):
    @abstractmethod
    def calculate(
        self,
        findings: ModelFindingsAbnormal,
        context: Context,
        config: Config
    ) -> SeverityLevel:
        pass


class ConfidenceBasedStrategy(SeverityStrategy):
    """
    Calculate severity based on:
    1. Attack ratio (what % of flows are attacks)
    2. Model confidence
    3. Attack type risk level
    4. Context (network zone, asset criticality)
    """

    # Attack types ranked by inherent risk
    HIGH_RISK_ATTACKS = {"DoS", "DDoS", "Botnet"}
    MEDIUM_RISK_ATTACKS = {"Brute Force", "Web Attack", "PortScan"}

    def calculate(
        self,
        findings: ModelFindingsAbnormal,
        context: Context,
        config: Config
    ) -> SeverityLevel:
        attack_ratio = findings.attack_ratio
        confidence = findings.confidence
        attack_type = findings.attack_type

        # Base severity from attack ratio
        # Model has ~15% FP rate, so thresholds start above that
        if attack_ratio < 0.25:
            severity = SeverityLevel.MEDIUM
        elif attack_ratio < 0.45:
            severity = SeverityLevel.HIGH
        else:
            severity = SeverityLevel.CRITICAL

        # Upgrade if attack type is high risk
        if attack_type in self.HIGH_RISK_ATTACKS:
            severity = self._upgrade(severity)

        # Upgrade if confidence is high and meaningful attack presence
        if confidence > 0.5 and attack_ratio > 0.3:
            severity = self._upgrade(severity)

        # Context-based upgrades
        if context.assetCriticality.value == "High":
            severity = self._upgrade(severity)

        if context.networkZone.value == "Internal":
            severity = self._upgrade(severity)

        return severity

    def _upgrade(self, severity: SeverityLevel) -> SeverityLevel:
        upgrade_map = {
            SeverityLevel.LOW: SeverityLevel.MEDIUM,
            SeverityLevel.MEDIUM: SeverityLevel.HIGH,
            SeverityLevel.HIGH: SeverityLevel.CRITICAL,
            SeverityLevel.CRITICAL: SeverityLevel.CRITICAL,
        }
        return upgrade_map[severity]

# Tuned thresholds for model FP tolerance

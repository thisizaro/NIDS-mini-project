import pytest
from app.models.schemas import (
    SeverityLevel, NetworkZone, AssetCriticality, 
    ModelFindingsAbnormal, Context
)
from app.services.severity_strategy import ReconstructionErrorStrategy
from app.config import Config


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def strategy():
    return ReconstructionErrorStrategy()


@pytest.fixture
def base_findings():
    return ModelFindingsAbnormal(
        status="abnormal",
        attack_detected=True,
        attack_type="PortScan",
        confidence=0.85,
        reconstruction_error=0.70,
        threshold=0.65,
        flow_count=100
    )


@pytest.fixture
def base_context():
    return Context(
        networkZone=NetworkZone.EXTERNAL,
        assetCriticality=AssetCriticality.LOW
    )


def test_base_severity_medium(strategy, config, base_findings, base_context):
    """Test base MEDIUM severity calculation"""
    base_findings.reconstruction_error = 0.70  # threshold * 1.07
    
    severity = strategy.calculate(base_findings, base_context, config)
    
    assert severity == SeverityLevel.MEDIUM


def test_base_severity_high(strategy, config, base_findings, base_context):
    """Test base HIGH severity calculation"""
    base_findings.reconstruction_error = 0.85  # threshold * 1.3
    
    severity = strategy.calculate(base_findings, base_context, config)
    
    assert severity == SeverityLevel.HIGH


def test_base_severity_critical(strategy, config, base_findings, base_context):
    """Test base CRITICAL severity calculation"""
    base_findings.reconstruction_error = 1.00  # threshold * 1.54
    
    severity = strategy.calculate(base_findings, base_context, config)
    
    assert severity == SeverityLevel.CRITICAL


def test_upgrade_for_high_risk_attack(strategy, config, base_findings, base_context):
    """Test severity upgrade for DDoS attack"""
    base_findings.attack_type = "DDoS"
    base_findings.reconstruction_error = 0.70  # Would be MEDIUM
    
    severity = strategy.calculate(base_findings, base_context, config)
    
    assert severity == SeverityLevel.HIGH  # Upgraded


def test_upgrade_for_high_criticality_asset(strategy, config, base_findings, base_context):
    """Test severity upgrade for high criticality asset"""
    base_findings.reconstruction_error = 0.70  # Would be MEDIUM
    base_context.assetCriticality = AssetCriticality.HIGH
    
    severity = strategy.calculate(base_findings, base_context, config)
    
    assert severity == SeverityLevel.HIGH  # Upgraded


def test_upgrade_for_internal_zone(strategy, config, base_findings, base_context):
    """Test severity upgrade for internal network zone"""
    base_findings.reconstruction_error = 0.70  # Would be MEDIUM
    base_context.networkZone = NetworkZone.INTERNAL
    
    severity = strategy.calculate(base_findings, base_context, config)
    
    assert severity == SeverityLevel.HIGH  # Upgraded


def test_multiple_upgrades_capped_at_critical(strategy, config, base_findings, base_context):
    """Test that multiple upgrades are capped at CRITICAL"""
    base_findings.attack_type = "Ransomware"  # +1
    base_findings.reconstruction_error = 0.85  # HIGH base
    base_context.assetCriticality = AssetCriticality.HIGH  # +1
    base_context.networkZone = NetworkZone.INTERNAL  # +1
    
    severity = strategy.calculate(base_findings, base_context, config)
    
    assert severity == SeverityLevel.CRITICAL  # Capped


def test_critical_stays_critical(strategy, config, base_findings, base_context):
    """Test that CRITICAL severity doesn't overflow"""
    base_findings.attack_type = "DDoS"
    base_findings.reconstruction_error = 1.50  # Already CRITICAL
    base_context.assetCriticality = AssetCriticality.HIGH
    
    severity = strategy.calculate(base_findings, base_context, config)
    
    assert severity == SeverityLevel.CRITICAL

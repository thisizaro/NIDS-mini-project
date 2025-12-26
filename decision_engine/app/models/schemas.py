from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NetworkZone(str, Enum):
    INTERNAL = "Internal"
    DMZ = "DMZ"
    EXTERNAL = "External"


class AssetCriticality(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AlertType(str, Enum):
    SOC = "SOC"
    FIREWALL = "Firewall"
    ADMIN = "Admin"
    SIEM = "SIEM"


class ModelFindingsNormal(BaseModel):
    status: str = Field(..., pattern="^normal$")
    attack_detected: bool = Field(False)
    confidence: float = Field(..., ge=0, le=1)
    flow_count: int = Field(..., ge=0)


class ModelFindingsAbnormal(BaseModel):
    status: str = Field(..., pattern="^abnormal$")
    attack_detected: bool
    attack_type: str
    confidence: float = Field(..., ge=0, le=1)
    attack_ratio: float = Field(0.0, ge=0, le=1)
    flow_count: int = Field(..., ge=0)
    class_distribution: Optional[Dict[str, int]] = None
    traffic_profile: Optional[Dict] = None


class Context(BaseModel):
    networkZone: NetworkZone
    assetCriticality: AssetCriticality


class VerdictRequest(BaseModel):
    modelFindings: dict
    context: Context


class VerdictResponse(BaseModel):
    verdict: SeverityLevel
    summary: str
    explanation: str
    inferredAttack: Optional[str] = None
    recommendedActions: List[str]
    alertsTriggered: List[AlertType]

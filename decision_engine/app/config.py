from pydantic_settings import BaseSettings


class Config(BaseSettings):
    APP_NAME: str = "Verdict Service"
    VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    
    # Severity thresholds
    MEDIUM_MULTIPLIER: float = 1.1
    HIGH_MULTIPLIER: float = 1.5
    CRITICAL_MULTIPLIER: float = 1.5
    
    # High-risk attack types
    HIGH_RISK_ATTACKS: list[str] = ["DDoS", "Ransomware"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


config = Config()

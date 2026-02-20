from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API Settings
    API_TITLE: str = "TruthChain API"
    API_VERSION: str = "1.0.0"
    
    # Database Settings
    DATABASE_URL: str = "postgresql://truthchain:truthchain_dev_password@localhost:5432/truthchain"
    
    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379"
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

from pydantic_settings import BaseSettings
from typing import List, Optional
import sys

_INSECURE_SECRET = "dev-secret-key-change-in-production"


class Settings(BaseSettings):
    # API Settings
    API_TITLE: str = "TruthChain API"
    API_VERSION: str = "1.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/truthchain"

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379"

    # Security
    SECRET_KEY: str = _INSECURE_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days

    # CORS — comma-separated list of allowed origins
    # e.g.  CORS_ORIGINS=https://app.example.com,https://admin.example.com
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # External AI / Search APIs
    TAVILY_API_KEY: str = ""   # https://app.tavily.com — required for web_verify rule type
    GROQ_API_KEY:   str = ""   # https://console.groq.com  — free, required for LLM proxy (Groq)
    OPENAI_API_KEY: str = ""   # https://platform.openai.com — optional for LLM proxy (OpenAI)

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS_ORIGINS as a Python list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    def validate_production(self) -> None:
        """Fail fast on unsafe production configuration."""
        if not self.is_production:
            return
        if self.SECRET_KEY == _INSECURE_SECRET:
            print("FATAL: SECRET_KEY must be changed before running in production!", flush=True)
            sys.exit(1)
        if "*" in self.cors_origins_list:
            print("FATAL: CORS_ORIGINS must not contain '*' in production!", flush=True)
            sys.exit(1)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
settings.validate_production()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings

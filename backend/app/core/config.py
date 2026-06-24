from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    DATABASE_URL: str
    # OpenRouter API key (replaces OPENAI_API_KEY)
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openai/gpt-4o"
    # HuggingFace for free embeddings (optional — leave blank to use anonymous)
    HF_API_KEY: Optional[str] = None
    HF_EMBED_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dims, free
    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    CRON_SECRET: Optional[str] = None
    # Microsoft / Azure AD OAuth
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_TENANT_ID: str = "common"
    AZURE_REDIRECT_URI: str = "http://localhost:8001/api/v1/auth/microsoft/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

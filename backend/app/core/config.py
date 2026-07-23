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
    # Microsoft / Azure AD OAuth
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_TENANT_ID: str = "common"
    AZURE_REDIRECT_URI: str = "http://localhost:8001/api/v1/auth/microsoft/callback"
    # Per-user Microsoft Graph "connect" flow for the in-app assistant (same Azure app
    # as sign-in). Scopes below are already admin-consented org-wide for app 7d7b5cc0.
    AZURE_CONNECT_REDIRECT_URI: str = "http://localhost:8001/api/v1/auth/microsoft/connect/callback"
    M365_GRAPH_SCOPES: List[str] = [
        "Mail.Read", "Mail.ReadWrite", "Calendars.Read",
        "OnlineMeetings.Read", "OnlineMeetingTranscript.Read.All",
    ]
    # Fernet key (urlsafe base64, 32 bytes) used to encrypt each user's stored MSAL
    # token cache at rest. Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    M365_TOKEN_ENC_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    # Shared secret for /internal/* endpoints (Railway Cron). Optional (C6): a
    # falsy value makes the internal endpoints return 401 rather than crashing
    # app boot, so local/test envs run with no cron secret configured.
    CRON_SECRET: Optional[str] = None

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

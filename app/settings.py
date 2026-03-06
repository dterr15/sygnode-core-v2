"""
Application settings — loaded from environment variables.
All secrets stay server-side (G4).
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # --- Database ---
    database_url: str = "postgresql+asyncpg://sygnode:sygnode@db:5432/sygnode"
    database_url_sync: str = "postgresql://sygnode:sygnode@db:5432/sygnode"

    # --- Auth ---
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    cookie_name: str = "sygnode_session"
    cookie_secure: bool = False  # True in production (HTTPS)
    cookie_samesite: str = "lax"

    # --- CORS ---
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    # --- Gemini (G4: server-side only, G6: explicit trigger only) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature_extraction: float = 0.1
    gemini_temperature_analysis: float = 0.3

    # --- Mailgun ---
    mailgun_api_key: str = ""
    mailgun_domain: str = "pxi.sygnode.cl"
    mailgun_from_email: str = "cotizaciones@pxi.sygnode.cl"

    # --- Google Workspace (Gmail) ---
    gws_client_email: str = ""
    gws_private_key: str = ""
    gws_impersonate_user: str = ""
    gws_project_id: str = ""
    gmail_webhook_token: str = ""  # HMAC token for G6

    # --- DataRoom NAS ---
    dataroom_api_url: str = ""
    dataroom_api_key: str = ""
    dataroom_enabled: bool = False

    # --- Cloudflare adapter (Wrap & Modernize) ---
    cf_adapter_url: str = "https://sygnode-core-engine.pages.dev/api"
    cf_adapter_enabled: bool = True
    r2_fallback_enabled: bool = True

    # --- Feature flags ---
    v2_intake: bool = True
    v2_rfqs: bool = True
    v2_traceability: bool = True
    v2_suppliers: bool = True
    v2_document_upload: bool = True

    # --- Environment ---
    environment: str = "development"
    log_level: str = "INFO"
    max_upload_size_mb: int = 25

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

settings = Settings()

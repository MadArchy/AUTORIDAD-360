from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # development | pilot | production
    app_env: str = "development"

    # Canónico: MySQL 8.4
    database_url: str = "mysql+pymysql://autoridad:autoridadpass@localhost:3307/autoridad360"
    redis_url: str = "redis://localhost:6379/0"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma4:e2b"
    vector_embedding_model: str = "ollama/nomic-embed-text"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    rss_extract_concurrency: int = 6
    rss_request_timeout_seconds: float = 15.0
    llm_request_timeout_seconds: float = 120.0
    content_critic_enabled: bool = False
    content_batch_generation_enabled: bool = True
    # Access corto; refresh vive en cookie HttpOnly.
    jwt_access_token_minutes: int = 30
    jwt_refresh_token_days: int = 14
    cookie_secure: bool = False
    # Publicación nativa: false = dry-run aunque la cuenta esté connected
    publish_native_live: bool = False
    dev_seed_password: str = "admin123"
    client_name: str = "Juan Vasquez"
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002"
    )

    # Secretos separados (Etapa 1)
    jwt_secret_key: str = "cambia-jwt-secret-en-produccion-min-32-chars"
    api_key_encryption_key: str = "cambia-encryption-key-en-produccion-min-32"
    session_secret_key: str = "cambia-session-secret-en-produccion-min-32"
    # Legacy alias → prefer api_key_encryption_key
    encryption_key: str = "cambia-encryption-key-en-produccion-min-32"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def allow_header_auth(self) -> bool:
        """X-User-Email solo en development/pilot — nunca en production."""
        return self.app_env.strip().lower() in {"development", "pilot", "dev"}

    @property
    def effective_encryption_key(self) -> str:
        return (self.api_key_encryption_key or self.encryption_key or "").strip()

    @property
    def effective_jwt_secret(self) -> str:
        return (self.jwt_secret_key or self.encryption_key or "").strip()

    def assert_secure_production(self) -> None:
        if not self.is_production:
            return
        values = {
            "JWT_SECRET_KEY": self.effective_jwt_secret,
            "API_KEY_ENCRYPTION_KEY": self.effective_encryption_key,
            "SESSION_SECRET_KEY": self.session_secret_key.strip(),
        }
        for name, value in values.items():
            if len(value) < 32 or value.startswith("cambia-"):
                raise RuntimeError(f"{name} must be a non-default secret of at least 32 characters")
        if len(set(values.values())) != len(values):
            raise RuntimeError("Production secrets must be distinct")


settings = Settings()

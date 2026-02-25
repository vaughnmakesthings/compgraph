from urllib.parse import quote, quote_plus, urlparse, urlunparse

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Supabase project identifiers
    SUPABASE_PROJECT_REF: str = "tkvxyxwfosworwqxesnz"
    SUPABASE_REGION: str = "us-west-2"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""  # anon key — safe for frontend, respects RLS

    # Auth (SEC-01)
    SUPABASE_JWT_SECRET: SecretStr = SecretStr("")  # HS256 secret for JWT verification
    SUPABASE_SERVICE_ROLE_KEY: SecretStr = SecretStr("")  # bypasses RLS, background jobs only
    AUTH_DISABLED: bool = False  # set True in tests to bypass auth middleware

    # Database password (stored separately to avoid URL-encoding issues with @, /, #)
    DATABASE_PASSWORD: str

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Proxy (optional — for residential proxy rotation)
    PROXY_URL: str | None = None
    PROXY_USERNAME: str | None = None
    PROXY_PASSWORD: SecretStr | None = None

    # Enrichment pipeline
    ENRICHMENT_BATCH_SIZE: int = 50
    ENRICHMENT_CONCURRENCY: int = 5
    ENRICHMENT_MODEL_PASS1: str = "claude-haiku-4-5-20251001"
    ENRICHMENT_MODEL_PASS2: str = "claude-sonnet-4-5-20250929"

    # Circuit breaker (consecutive group-level API failures before aborting batch)
    ENRICHMENT_CIRCUIT_BREAKER_THRESHOLD: int = 3

    # Entity resolution thresholds (fuzzy matching via rapidfuzz)
    ENTITY_AUTO_ACCEPT_THRESHOLD: int = 85
    ENTITY_REVIEW_THRESHOLD: int = 70

    # Alembic (optional override — used when direct host DNS fails)
    ALEMBIC_DATABASE_URL: str | None = None

    # Scheduler
    SCHEDULER_ENABLED: bool = False
    SCHEDULER_PIPELINE_CRON: str = "0 2 * * 1,3,5"  # Mon/Wed/Fri 2am
    SCHEDULER_TIMEZONE: str = "America/New_York"

    # Connection pool
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 3
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 300

    # Dashboard connection pool (sync, smaller)
    DASHBOARD_DB_POOL_SIZE: int = 2
    DASHBOARD_DB_MAX_OVERFLOW: int = 1
    DASHBOARD_DB_POOL_TIMEOUT: int = 30
    DASHBOARD_DB_POOL_RECYCLE: int = 300

    # Sentry
    SENTRY_DSN: str = ""  # empty = disabled

    # App config
    ENVIRONMENT: str = "dev"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "*"

    @model_validator(mode="after")
    def _auth_safety_check(self) -> "Settings":
        if self.AUTH_DISABLED and self.ENVIRONMENT == "production":
            raise ValueError("AUTH_DISABLED=true is forbidden when ENVIRONMENT=production")
        return self

    @model_validator(mode="after")
    def _jwt_secret_required(self) -> "Settings":
        if not self.AUTH_DISABLED:
            secret = self.SUPABASE_JWT_SECRET.get_secret_value()
            if len(secret) < 32:
                raise ValueError(
                    "SUPABASE_JWT_SECRET must be at least 32 bytes when auth is "
                    "enabled (AUTH_DISABLED=False). Get it from Supabase Dashboard "
                    "> Project Settings > API."
                )
        return self

    @property
    def database_url(self) -> str:
        """Session mode pooler URL for app traffic (IPv4 compatible)."""
        pw = quote_plus(self.DATABASE_PASSWORD)
        return (
            f"postgresql+asyncpg://postgres.{self.SUPABASE_PROJECT_REF}:{pw}"
            f"@aws-0-{self.SUPABASE_REGION}.pooler.supabase.com:5432/postgres"
        )

    @property
    def database_url_direct(self) -> str:
        """Direct connection URL for Alembic migrations (bypasses pooler)."""
        pw = quote_plus(self.DATABASE_PASSWORD)
        return (
            f"postgresql+asyncpg://postgres:{pw}"
            f"@db.{self.SUPABASE_PROJECT_REF}.supabase.co:5432/postgres"
        )

    @property
    def proxy_url_with_auth(self) -> str | None:
        """Proxy URL with embedded credentials if username/password are provided."""
        if not self.PROXY_URL:
            return None
        if not self.PROXY_USERNAME:
            return self.PROXY_URL

        parsed = urlparse(self.PROXY_URL)
        # Use quote() not quote_plus() — userinfo uses percent-encoding per RFC 3986
        auth = quote(self.PROXY_USERNAME, safe="")
        if self.PROXY_PASSWORD:
            auth += f":{quote(self.PROXY_PASSWORD.get_secret_value(), safe='')}"
        # Preserve IPv6 brackets around hostname
        host = parsed.hostname or ""
        if ":" in host:
            host = f"[{host}]"
        netloc = f"{auth}@{host}"
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()  # type: ignore[call-arg]  # populated by pydantic-settings from env

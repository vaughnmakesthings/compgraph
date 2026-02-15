from urllib.parse import quote_plus, urlparse, urlunparse

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Supabase project identifiers
    SUPABASE_PROJECT_REF: str = "tkvxyxwfosworwqxesnz"
    SUPABASE_REGION: str = "us-west-2"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # Database password (stored separately to avoid URL-encoding issues with @, /, #)
    DATABASE_PASSWORD: str

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Proxy (optional — for residential proxy rotation)
    PROXY_URL: str | None = None
    PROXY_USERNAME: str | None = None
    PROXY_PASSWORD: SecretStr | None = None

    # App config
    ENVIRONMENT: str = "dev"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "*"

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
        auth = quote_plus(self.PROXY_USERNAME)
        if self.PROXY_PASSWORD:
            auth += f":{quote_plus(self.PROXY_PASSWORD.get_secret_value())}"
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

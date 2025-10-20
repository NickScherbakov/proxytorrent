"""Core configuration management using pydantic-settings."""
import secrets
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseSettings):
    """Security and authentication settings."""

    auth_enabled: bool = Field(default=True, description="Enable authentication")
    hmac_secret: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        description="HMAC secret for request signing",
    )
    bearer_tokens: list[str] = Field(
        default_factory=list, description="List of valid bearer tokens"
    )
    token_header: str = Field(default="Authorization", description="Auth header name")


class ProxySettings(BaseSettings):
    """Proxy/VPN configuration."""

    proxy_enabled: bool = Field(default=True, description="Enforce proxy usage")
    proxy_type: Literal["http", "https", "socks5"] = Field(
        default="socks5", description="Proxy type"
    )
    proxy_host: str | None = Field(default=None, description="Proxy host")
    proxy_port: int | None = Field(default=None, description="Proxy port")
    proxy_username: str | None = Field(default=None, description="Proxy username")
    proxy_password: str | None = Field(default=None, description="Proxy password")

    @property
    def proxy_url(self) -> str | None:
        """Build proxy URL from settings."""
        if not self.proxy_host or not self.proxy_port:
            return None

        auth = ""
        if self.proxy_username and self.proxy_password:
            auth = f"{self.proxy_username}:{self.proxy_password}@"

        return f"{self.proxy_type}://{auth}{self.proxy_host}:{self.proxy_port}"


class FetcherSettings(BaseSettings):
    """Fetcher service configuration."""

    connect_timeout: int = Field(default=10, description="Connection timeout in seconds")
    read_timeout: int = Field(default=30, description="Read timeout in seconds")
    max_size: int = Field(default=50 * 1024 * 1024, description="Max response size in bytes")
    mime_whitelist: list[str] = Field(
        default_factory=lambda: [
            "text/html",
            "text/plain",
            "application/json",
            "application/xml",
            "image/*",
        ],
        description="Allowed MIME types",
    )
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    user_agent: str = Field(
        default="ProxyTorrent/0.1.0", description="User agent for requests"
    )


class TorrentSettings(BaseSettings):
    """Torrent creation and seeding configuration."""

    private_tracker: bool = Field(default=True, description="Create private torrents")
    piece_size: int = Field(default=256 * 1024, description="Torrent piece size in bytes")
    announce_url: str | None = Field(
        default=None, description="Tracker announce URL"
    )
    encryption_enabled: bool = Field(default=True, description="Enable torrent encryption")
    upload_rate_limit: int = Field(default=0, description="Upload rate limit (0=unlimited)")
    download_rate_limit: int = Field(default=0, description="Download rate limit (0=unlimited)")
    max_connections: int = Field(default=200, description="Max peer connections")


class StorageSettings(BaseSettings):
    """Storage backend configuration."""

    storage_type: Literal["filesystem"] = Field(
        default="filesystem", description="Storage backend type"
    )
    base_path: Path = Field(
        default=Path("./data"), description="Base storage path"
    )
    content_path: Path = Field(
        default=Path("./data/content"), description="Content storage path"
    )
    torrent_path: Path = Field(
        default=Path("./data/torrents"), description="Torrent file storage path"
    )
    resume_path: Path = Field(
        default=Path("./data/resume"), description="Resume data storage path"
    )

    @field_validator("base_path", "content_path", "torrent_path", "resume_path")
    @classmethod
    def ensure_absolute(cls, v: Path) -> Path:
        """Ensure paths are absolute."""
        return v.resolve()


class CacheSettings(BaseSettings):
    """Caching configuration."""

    cache_enabled: bool = Field(default=True, description="Enable request caching")
    default_ttl: int = Field(default=3600, description="Default cache TTL in seconds")
    max_ttl: int = Field(default=86400, description="Maximum cache TTL in seconds")
    redis_url: str | None = Field(
        default=None, description="Redis URL for distributed cache"
    )


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration."""

    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    requests_per_minute: int = Field(
        default=60, description="Max requests per minute per user"
    )
    requests_per_hour: int = Field(
        default=1000, description="Max requests per hour per user"
    )
    requests_per_ip_minute: int = Field(
        default=100, description="Max requests per minute per IP"
    )


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/proxytorrent.db",
        description="Database connection URL",
    )
    echo_sql: bool = Field(default=False, description="Echo SQL queries")


class MonitoringSettings(BaseSettings):
    """Monitoring and logging configuration."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Log level"
    )
    json_logs: bool = Field(default=True, description="Use JSON log formatting")
    mask_sensitive: bool = Field(
        default=True, description="Mask sensitive data in logs"
    )
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Service info
    app_name: str = Field(default="ProxyTorrent", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")

    # API settings
    api_prefix: str = Field(default="/v1", description="API path prefix")
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")

    # Sub-settings
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    fetcher: FetcherSettings = Field(default_factory=FetcherSettings)
    torrent: TorrentSettings = Field(default_factory=TorrentSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)

    def initialize_storage(self) -> None:
        """Create storage directories if they don't exist."""
        for path_attr in ["base_path", "content_path", "torrent_path", "resume_path"]:
            path = getattr(self.storage, path_attr)
            path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

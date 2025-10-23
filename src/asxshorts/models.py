"""Pydantic models for data validation and settings management."""

import os
import platform
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ShortRecord(BaseModel):
    """Model for a single short selling record."""

    report_date: date = Field(..., description="Date of the report")
    asx_code: str = Field(
        ..., min_length=1, max_length=10, description="ASX stock code"
    )
    company_name: str | None = Field(None, description="Company name")
    short_sold: int | str | None = Field(
        None, description="Number of shares sold short"
    )
    issued_shares: int | str | None = Field(None, description="Total shares issued")
    percent_short: float | str | None = Field(
        None, description="Percentage of shares sold short"
    )
    raw: dict[str, Any] = Field(default_factory=dict, description="Raw data from CSV")

    @field_validator("asx_code")
    @classmethod
    def validate_asx_code(cls: type["ShortRecord"], v: str) -> str:
        """Validate and normalize ASX code."""
        if not v or not v.strip():
            raise ValueError("ASX code cannot be empty")
        return v.strip().upper()

    @field_validator("short_sold", "issued_shares")
    @classmethod
    def validate_share_counts(
        cls: type["ShortRecord"], v: int | str | None
    ) -> int | str | None:
        """Validate share count fields."""
        if v is None:
            return None
        if isinstance(v, str):
            # Try to convert to int, but keep as string if it fails
            try:
                return int(v.replace(",", "").replace(" ", ""))
            except (ValueError, AttributeError):
                return v
        return v

    @field_validator("percent_short")
    @classmethod
    def validate_percent_short(
        cls: type["ShortRecord"], v: float | str | None
    ) -> float | str | None:
        """Validate percentage field."""
        if v is None:
            return None
        if isinstance(v, str):
            # Try to convert to float, but keep as string if it fails
            try:
                clean_v = v.replace("%", "").replace(",", "").strip()
                return float(clean_v)
            except (ValueError, AttributeError):
                return v
        return v

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


def _platform_default_cache_dir() -> str:
    """Return a platform-appropriate default cache directory for this app."""
    system = platform.system().lower()
    app_name = "asxshorts"
    try:
        if system == "windows":
            root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            if root:
                return str(Path(root) / app_name)
        elif system == "darwin":
            return str(Path.home() / "Library" / "Caches" / app_name)
        # Default to XDG cache home or ~/.cache
        xdg = os.environ.get("XDG_CACHE_HOME")
        if xdg:
            return str(Path(xdg) / app_name)
        return str(Path.home() / ".cache" / app_name)
    except Exception:
        # Fallback to ~/.cache as a last resort
        return str(Path.home() / ".cache" / app_name)


class ClientSettings(BaseSettings):
    """Settings for the ShortsClient with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="asxshorts_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core settings
    cache_dir: str = Field(
        default_factory=_platform_default_cache_dir,
        description="Directory for caching files",
    )
    base_url: str = Field(
        default="https://download.asic.gov.au", description="Base URL for ASIC/ASX data"
    )
    user_agent: str = Field(
        default="asxshorts (+https://github.com/ay-mich/asxshorts)",
        description="User agent string for requests",
    )

    # Request settings
    timeout: float = Field(
        default=20.0, gt=0, le=300, description="Request timeout in seconds"
    )
    retries: int = Field(default=0, ge=0, le=10, description="Number of retry attempts")
    backoff: float = Field(
        default=0.5, gt=0, le=10, description="Exponential backoff base for retries"
    )
    http_adapter_retries: bool = Field(
        default=True,
        description="Enable urllib3 HTTPAdapter retry strategy at the session level.",
    )

    # Cache settings
    max_cache_age_days: int = Field(
        default=30, ge=1, le=365, description="Maximum age of cache files in days"
    )
    cache_lock_timeout: float = Field(
        default=30.0,
        gt=0,
        le=300,
        description="Timeout for cache file locks in seconds",
    )

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Logging format string",
    )

    # Publish lag settings
    publish_lag_days: int = Field(
        default=7,
        ge=1,
        le=14,
        description="Expected ASIC publish lag window in days (for messaging)",
    )

    @field_validator("cache_dir")
    @classmethod
    def validate_cache_dir(cls: type["ClientSettings"], v: str) -> str:
        """Validate and expand cache directory path."""
        return str(Path(v).expanduser().resolve())

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls: type["ClientSettings"], v: str) -> str:
        """Validate base URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls: type["ClientSettings"], v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper


class CacheStats(BaseModel):
    """Model for cache statistics."""

    count: int = Field(..., ge=0, description="Number of cached files")
    size_bytes: int = Field(..., ge=0, description="Total size in bytes")
    path: str = Field(..., description="Cache directory path")
    oldest_file: date | None = Field(None, description="Date of oldest cached file")
    newest_file: date | None = Field(None, description="Date of newest cached file")

    @property
    def size_mb(self) -> float:
        """Size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    @property
    def size_human(self) -> str:
        """Human-readable size."""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size_bytes / (1024 * 1024 * 1024):.1f} GB"


class FetchResult(BaseModel):
    """Model for fetch operation results."""

    fetch_date: date = Field(..., description="Date that was fetched")
    record_count: int = Field(..., ge=0, description="Number of records fetched")
    from_cache: bool = Field(..., description="Whether data came from cache")
    fetch_time_ms: float = Field(..., ge=0, description="Fetch time in milliseconds")
    url: str | None = Field(None, description="URL that was fetched")
    records: list["ShortRecord"] = Field(
        default_factory=list, description="The actual records"
    )

    model_config = ConfigDict(validate_assignment=True)


class RangeResult(BaseModel):
    """Model for date range fetch results."""

    start_date: date = Field(..., description="Start date of range")
    end_date: date = Field(..., description="End date of range")
    total_records: int = Field(..., ge=0, description="Total records across all dates")
    successful_dates: list[date] = Field(
        default_factory=list, description="Dates successfully fetched"
    )
    failed_dates: list[date] = Field(
        default_factory=list, description="Dates that failed to fetch"
    )
    total_fetch_time_ms: float = Field(
        ..., ge=0, description="Total fetch time in milliseconds"
    )
    results: dict[date, "FetchResult"] = Field(
        default_factory=dict, description="Results for each date"
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "RangeResult":
        """Validate that start_date <= end_date."""
        if self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")
        return self

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        total_days = (self.end_date - self.start_date).days + 1
        if total_days == 0:
            return 100.0
        return (len(self.successful_dates) / total_days) * 100

    model_config = ConfigDict(validate_assignment=True)

    def __len__(self) -> int:
        """Number of successful dates.

        Provides a sensible length for interactive use, e.g., len(range_result).
        """
        return len(self.successful_dates)

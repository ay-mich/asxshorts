"""Tests for asxshorts.models module."""

import tempfile
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from asxshorts.models import (
    CacheStats,
    ClientSettings,
    FetchResult,
    RangeResult,
    ShortRecord,
    _platform_default_cache_dir,
)


class TestShortRecord:
    """Test ShortRecord model."""

    def test_valid_record(self):
        """Test creating a valid ShortRecord."""
        record = ShortRecord(
            report_date=date(2024, 1, 15),
            asx_code="CBA",
            company_name="Commonwealth Bank",
            short_sold=1000,
            issued_shares=100000,
            percent_short=1.0,
            raw={"test": "data"},
        )

        assert record.report_date == date(2024, 1, 15)
        assert record.asx_code == "CBA"
        assert record.company_name == "Commonwealth Bank"
        assert record.short_sold == 1000
        assert record.issued_shares == 100000
        assert record.percent_short == 1.0
        assert record.raw == {"test": "data"}

    def test_minimal_record(self):
        """Test creating a minimal ShortRecord with only required fields."""
        record = ShortRecord(report_date=date(2024, 1, 15), asx_code="CBA")

        assert record.report_date == date(2024, 1, 15)
        assert record.asx_code == "CBA"
        assert record.company_name is None
        assert record.short_sold is None
        assert record.issued_shares is None
        assert record.percent_short is None
        assert record.raw == {}

    def test_asx_code_validation(self):
        """Test ASX code validation."""
        # Valid codes
        record = ShortRecord(report_date=date(2024, 1, 15), asx_code="  cba  ")
        assert record.asx_code == "CBA"  # Should be stripped and uppercased

        # Invalid codes
        with pytest.raises(
            ValidationError, match="String should have at least 1 character"
        ):
            ShortRecord(report_date=date(2024, 1, 15), asx_code="")

        with pytest.raises(
            ValidationError, match="String should have at least 1 character"
        ):
            ShortRecord(report_date=date(2024, 1, 15), asx_code="   ")

    def test_share_count_validation(self):
        """Test share count field validation."""
        # String with commas
        record = ShortRecord(
            report_date=date(2024, 1, 15),
            asx_code="CBA",
            short_sold="1,000,000",
            issued_shares="100 000 000",
        )
        assert record.short_sold == 1000000
        assert record.issued_shares == 100000000

        # Invalid string that can't be converted
        record = ShortRecord(
            report_date=date(2024, 1, 15),
            asx_code="CBA",
            short_sold="invalid",
            issued_shares="also invalid",
        )
        assert record.short_sold == "invalid"
        assert record.issued_shares == "also invalid"

    def test_percent_short_validation(self):
        """Test percentage field validation."""
        # String with percentage sign
        record = ShortRecord(
            report_date=date(2024, 1, 15), asx_code="CBA", percent_short="5.5%"
        )
        assert record.percent_short == 5.5

        # String with commas
        record = ShortRecord(
            report_date=date(2024, 1, 15), asx_code="CBA", percent_short="1,000.5"
        )
        assert record.percent_short == 1000.5

        # Invalid string
        record = ShortRecord(
            report_date=date(2024, 1, 15), asx_code="CBA", percent_short="invalid"
        )
        assert record.percent_short == "invalid"

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ShortRecord()  # Missing required fields

        with pytest.raises(ValidationError):
            ShortRecord(report_date=date(2024, 1, 15))  # Missing asx_code

        with pytest.raises(ValidationError):
            ShortRecord(asx_code="CBA")  # Missing report_date


class TestClientSettings:
    """Test ClientSettings model."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = ClientSettings()

        # Check that cache_dir equals platform default
        assert settings.cache_dir == str(
            Path(_platform_default_cache_dir()).expanduser().resolve()
        )
        assert settings.base_url == "https://download.asic.gov.au"
        assert "asxshorts" in settings.user_agent
        assert settings.timeout == 20.0
        assert settings.retries == 0
        assert settings.backoff == 0.5
        assert settings.max_cache_age_days == 30
        assert settings.cache_lock_timeout == 30.0
        assert settings.log_level == "INFO"

    def test_custom_settings(self):
        """Test custom settings values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = ClientSettings(
                cache_dir=tmpdir,
                base_url="https://custom.example.com",
                timeout=10.0,
                retries=5,
                log_level="DEBUG",
            )

            assert settings.cache_dir == str(Path(tmpdir).resolve())
            assert settings.base_url == "https://custom.example.com"
            assert settings.timeout == 10.0
            assert settings.retries == 5
            assert settings.log_level == "DEBUG"

    def test_cache_dir_validation(self):
        """Test cache directory path validation."""
        settings = ClientSettings(cache_dir="~/test-cache")
        assert settings.cache_dir == str(Path("~/test-cache").expanduser().resolve())

    def test_base_url_validation(self):
        """Test base URL validation."""
        # Valid URLs
        settings = ClientSettings(base_url="https://example.com/")
        assert settings.base_url == "https://example.com"  # Trailing slash removed

        settings = ClientSettings(base_url="http://example.com")
        assert settings.base_url == "http://example.com"

        # Invalid URLs
        with pytest.raises(ValidationError, match="Base URL must start with http"):
            ClientSettings(base_url="ftp://example.com")

        with pytest.raises(ValidationError, match="Base URL must start with http"):
            ClientSettings(base_url="example.com")

    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = ClientSettings(log_level=level)
            assert settings.log_level == level

        # Case insensitive
        settings = ClientSettings(log_level="debug")
        assert settings.log_level == "DEBUG"

        # Invalid level
        with pytest.raises(ValidationError, match="Log level must be one of"):
            ClientSettings(log_level="INVALID")

    def test_validation_ranges(self):
        """Test validation ranges for numeric fields."""
        # Valid values
        settings = ClientSettings(
            timeout=1.0,
            retries=0,
            backoff=0.1,
            max_cache_age_days=1,
            cache_lock_timeout=1.0,
        )
        assert settings.timeout == 1.0
        assert settings.retries == 0

        # Invalid values
        with pytest.raises(ValidationError):
            ClientSettings(timeout=0)  # Must be > 0

        with pytest.raises(ValidationError):
            ClientSettings(timeout=400)  # Must be <= 300

        with pytest.raises(ValidationError):
            ClientSettings(retries=-1)  # Must be >= 0

        with pytest.raises(ValidationError):
            ClientSettings(retries=15)  # Must be <= 10


class TestCacheStats:
    """Test CacheStats model."""

    def test_cache_stats_creation(self):
        """Test creating CacheStats."""
        stats = CacheStats(
            count=10,
            size_bytes=1024000,
            path="/tmp/cache",
            oldest_file=date(2024, 1, 1),
            newest_file=date(2024, 1, 15),
        )

        assert stats.count == 10
        assert stats.size_bytes == 1024000
        assert stats.path == "/tmp/cache"
        assert stats.oldest_file == date(2024, 1, 1)
        assert stats.newest_file == date(2024, 1, 15)

    def test_size_properties(self):
        """Test size calculation properties."""
        stats = CacheStats(
            count=1,
            size_bytes=1572864,  # Exactly 1.5 MB
            path="/tmp/cache",
        )

        assert stats.size_mb == 1.5
        assert stats.size_human == "1.5 MB"

        # Test different size ranges
        stats_bytes = CacheStats(count=1, size_bytes=512, path="/tmp")
        assert stats_bytes.size_human == "512 B"

        stats_kb = CacheStats(count=1, size_bytes=1536, path="/tmp")
        assert stats_kb.size_human == "1.5 KB"

        stats_gb = CacheStats(count=1, size_bytes=1610612736, path="/tmp")  # 1.5 GB
        assert stats_gb.size_human == "1.5 GB"

    def test_optional_fields(self):
        """Test optional fields."""
        stats = CacheStats(count=0, size_bytes=0, path="/tmp/cache")
        assert stats.oldest_file is None
        assert stats.newest_file is None


class TestFetchResult:
    """Test FetchResult model."""

    def test_fetch_result_creation(self):
        """Test creating FetchResult."""
        result = FetchResult(
            fetch_date=date(2024, 1, 15),
            record_count=100,
            from_cache=True,
            fetch_time_ms=250.5,
            url="https://example.com/data.csv",
        )

        assert result.fetch_date == date(2024, 1, 15)
        assert result.record_count == 100
        assert result.from_cache is True
        assert result.fetch_time_ms == 250.5
        assert result.url == "https://example.com/data.csv"

    def test_optional_url(self):
        """Test optional URL field."""
        result = FetchResult(
            fetch_date=date(2024, 1, 15),
            record_count=0,
            from_cache=True,
            fetch_time_ms=0.0,
        )
        assert result.url is None

    def test_validation_constraints(self):
        """Test validation constraints."""
        # Valid values
        result = FetchResult(
            fetch_date=date(2024, 1, 15),
            record_count=0,
            from_cache=False,
            fetch_time_ms=0.0,
        )
        assert result.record_count == 0
        assert result.fetch_time_ms == 0.0

        # Invalid values
        with pytest.raises(ValidationError):
            FetchResult(
                fetch_date=date(2024, 1, 15),
                record_count=-1,  # Must be >= 0
                from_cache=False,
                fetch_time_ms=0.0,
            )

        with pytest.raises(ValidationError):
            FetchResult(
                fetch_date=date(2024, 1, 15),
                record_count=0,
                from_cache=False,
                fetch_time_ms=-1.0,  # Must be >= 0
            )


class TestRangeResult:
    """Test RangeResult model."""

    def test_range_result_creation(self):
        """Test creating RangeResult."""
        result = RangeResult(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 17),
            total_records=150,
            successful_dates=[date(2024, 1, 15), date(2024, 1, 17)],
            failed_dates=[date(2024, 1, 16)],
            total_fetch_time_ms=500.0,
        )

        assert result.start_date == date(2024, 1, 15)
        assert result.end_date == date(2024, 1, 17)
        assert result.total_records == 150
        assert len(result.successful_dates) == 2
        assert len(result.failed_dates) == 1
        assert result.total_fetch_time_ms == 500.0

    def test_default_lists(self):
        """Test default empty lists."""
        result = RangeResult(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            total_records=0,
            total_fetch_time_ms=0.0,
        )

        assert result.successful_dates == []
        assert result.failed_dates == []

    def test_date_range_validation(self):
        """Test date range validation."""
        # Valid range
        result = RangeResult(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),  # Same date is valid
            total_records=0,
            total_fetch_time_ms=0.0,
        )
        assert result.start_date == result.end_date

        # Invalid range - this should raise ValidationError
        with pytest.raises(ValidationError, match="start_date must be <= end_date"):
            RangeResult(
                start_date=date(2024, 1, 17),
                end_date=date(2024, 1, 15),  # end < start
                total_records=0,
                total_fetch_time_ms=0.0,
            )

    def test_validation_constraints(self):
        """Test validation constraints."""
        # Valid values
        result = RangeResult(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            total_records=0,
            total_fetch_time_ms=0.0,
        )
        assert result.total_records == 0
        assert result.total_fetch_time_ms == 0.0

        # Invalid values
        with pytest.raises(ValidationError):
            RangeResult(
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 15),
                total_records=-1,  # Must be >= 0
                total_fetch_time_ms=0.0,
            )

        with pytest.raises(ValidationError):
            RangeResult(
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 15),
                total_records=0,
                total_fetch_time_ms=-1.0,  # Must be >= 0
            )

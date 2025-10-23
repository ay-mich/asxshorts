"""Tests for ShortsClient."""

import os
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from asxshorts.client import ShortsClient
from asxshorts.errors import NotFoundError
from asxshorts.models import (
    CacheStats,
    ClientSettings,
    FetchResult,
    RangeResult,
)


class TestShortsClient:
    """Test cases for ShortsClient."""

    def test_init_default(self):
        """Test client initialization with defaults."""
        client = ShortsClient()
        assert client.settings.base_url == "https://download.asic.gov.au"
        assert client.settings.timeout == 20.0
        assert client.settings.retries == 0
        assert client.cache is not None
        assert client.session is not None
        assert client.resolver is not None

    def test_init_custom_params(self):
        """Test client initialization with custom parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = ClientSettings(
                cache_dir=tmpdir,
                base_url="https://example.com",
                timeout=10.0,
                retries=5,
            )
            client = ShortsClient(settings=settings)
            assert str(client.settings.cache_dir) == str(Path(tmpdir).resolve())
            assert client.settings.base_url == "https://example.com"
            assert client.settings.timeout == 10.0
            assert client.settings.retries == 5

    @patch("asxshorts.client.requests.Session")
    def test_create_session(self, mock_session_class):
        """Test session creation with retry configuration."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        client = ShortsClient()

        # Verify session was configured
        mock_session.headers.update.assert_called_once()
        mock_session.mount.assert_called()

    def test_context_manager(self):
        """Test client as context manager."""
        with ShortsClient() as client:
            assert client is not None
            assert hasattr(client.session, "close")

    @patch("asxshorts.client.ShortsClient._fetch_with_retry")
    @patch("asxshorts.client.validate_records")
    @patch("asxshorts.client.parse_csv_content")
    @patch("asxshorts.cache.CacheManager.read_cached")
    def test_fetch_day_success(
        self, mock_cache_read, mock_parse, mock_validate, mock_fetch
    ):
        """Test successful fetch_day operation."""
        # Setup mocks
        test_date = date(2024, 1, 15)
        mock_content = b"test,csv,content"
        mock_records = [
            {
                "report_date": test_date,
                "asx_code": "TEST",
                "short_sold": 100,
                "issued_shares": 1000,
                "percent_short": 10.0,
                "raw": {"date": "2024-01-15", "product": "TEST", "short_qty": 100},
            }
        ]

        mock_cache_read.return_value = None  # Force fresh fetch
        mock_fetch.return_value = mock_content
        mock_parse.return_value = mock_records
        mock_validate.return_value = mock_records

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = ClientSettings(cache_dir=tmpdir)
            client = ShortsClient(settings=settings)

            # Mock resolver
            client.resolver = Mock()
            client.resolver.url_for.return_value = "https://example.com/test.csv"

            result = client.fetch_day(test_date)

            assert isinstance(result, FetchResult)
            assert result.fetch_date == test_date
            assert result.record_count == 1
            assert isinstance(result.fetch_time_ms, float)
            assert result.from_cache == False
            mock_fetch.assert_called_once_with("https://example.com/test.csv")
            mock_parse.assert_called_once_with(mock_content, test_date)

    def test_fetch_day_not_found(self):
        """Test fetch_day when URL not found."""
        test_date = date(2024, 1, 15)

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = ClientSettings(cache_dir=tmpdir)
            client = ShortsClient(settings=settings)

            # Mock resolver to raise NotFoundError
            client.resolver = Mock()
            client.resolver.url_for.side_effect = NotFoundError(test_date)

            with pytest.raises(NotFoundError):
                client.fetch_day(test_date)

    @patch("asxshorts.client.ShortsClient.fetch_day")
    def test_fetch_range_success(self, mock_fetch_day):
        """Test successful fetch_range operation."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 17)

        # Mock fetch_day to return FetchResult objects
        mock_fetch_day.side_effect = [
            FetchResult(
                fetch_date=date(2024, 1, 15),
                record_count=1,
                from_cache=False,
                fetch_time_ms=100.0,
            ),
            FetchResult(
                fetch_date=date(2024, 1, 16),
                record_count=2,
                from_cache=False,
                fetch_time_ms=150.0,
            ),
            FetchResult(
                fetch_date=date(2024, 1, 17),
                record_count=1,
                from_cache=False,
                fetch_time_ms=120.0,
            ),
        ]

        client = ShortsClient()
        result = client.fetch_range(start_date, end_date)

        assert isinstance(result, RangeResult)
        assert result.start_date == start_date
        assert result.end_date == end_date
        assert result.total_records == 4  # 1 + 2 + 1
        assert len(result.successful_dates) == 3
        assert len(result.failed_dates) == 0
        assert mock_fetch_day.call_count == 3

    def test_fetch_range_invalid_dates(self):
        """Test fetch_range with invalid date range."""
        start_date = date(2024, 1, 17)
        end_date = date(2024, 1, 15)

        client = ShortsClient()

        with pytest.raises(ValueError, match="start_date must be <= end_date"):
            client.fetch_range(start_date, end_date)

    @patch("asxshorts.client.ShortsClient.fetch_day")
    def test_fetch_range_with_failures(self, mock_fetch_day):
        """Test fetch_range handling partial failures."""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 17)

        # Mock fetch_day with some failures
        mock_fetch_day.side_effect = [
            FetchResult(
                fetch_date=date(2024, 1, 15),
                record_count=1,
                from_cache=False,
                fetch_time_ms=100.0,
            ),
            NotFoundError(date(2024, 1, 16)),
            FetchResult(
                fetch_date=date(2024, 1, 17),
                record_count=1,
                from_cache=False,
                fetch_time_ms=120.0,
            ),
        ]

        client = ShortsClient()
        result = client.fetch_range(start_date, end_date)

        # Should return RangeResult with successful and failed dates
        assert isinstance(result, RangeResult)
        assert result.total_records == 2  # 1 + 1
        assert len(result.successful_dates) == 2
        assert len(result.failed_dates) == 1
        assert date(2024, 1, 15) in result.successful_dates
        assert date(2024, 1, 17) in result.successful_dates
        assert date(2024, 1, 16) in result.failed_dates

    def test_cache_stats(self):
        """Test cache_stats method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = ClientSettings(cache_dir=tmpdir)
            client = ShortsClient(settings=settings)
            stats = client.cache_stats()

            assert isinstance(stats, CacheStats)
            assert stats.count == 0  # Empty cache
            assert stats.size_bytes == 0
            assert str(stats.path) == str(Path(tmpdir).resolve())

    def test_clear_cache(self):
        """Test clear_cache method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = ClientSettings(cache_dir=tmpdir)
            client = ShortsClient(settings=settings)

            # Create a dummy cache file
            cache_file = os.path.join(tmpdir, "2024-01-15.csv")
            with open(cache_file, "w") as f:
                f.write("test,data")

            # Verify file exists
            assert os.path.exists(cache_file)

            # Clear cache
            client.clear_cache()

            # Verify file is removed
            assert not os.path.exists(cache_file)

    @patch("time.time")
    def test_cleanup_cache(self, mock_time):
        """Test cleanup_cache method."""
        # Mock current time
        current_time = 1000000000  # Some timestamp
        mock_time.return_value = current_time

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = ClientSettings(cache_dir=tmpdir)
            client = ShortsClient(settings=settings)

            # Create old and new cache files
            old_file = os.path.join(tmpdir, "old.csv")
            new_file = os.path.join(tmpdir, "new.csv")

            with open(old_file, "w") as f:
                f.write("old")
            with open(new_file, "w") as f:
                f.write("new")

            # Set file modification times
            old_time = current_time - (31 * 24 * 3600)  # 31 days ago
            new_time = current_time - (1 * 24 * 3600)  # 1 day ago

            os.utime(old_file, (old_time, old_time))
            os.utime(new_file, (new_time, new_time))

            # Cleanup files older than 30 days
            client.cleanup_cache(max_age_days=30)

            # Old file should be removed, new file should remain
            assert not os.path.exists(old_file)
            assert os.path.exists(new_file)

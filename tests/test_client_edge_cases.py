"""Edge case tests for client.py to improve coverage."""

import time
from datetime import date
from unittest.mock import Mock, patch

import pytest
import requests

from asxshorts.client import ShortsClient
from asxshorts.errors import FetchError, NotFoundError, RateLimitError
from asxshorts.models import ClientSettings, FetchResult, ShortRecord


@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    return Mock(spec=requests.Session)


@pytest.fixture
def mock_resolver():
    """Create a mock URL resolver."""
    resolver = Mock()
    resolver.url_for.return_value = "https://example.com/test.csv"
    return resolver


@pytest.fixture
def mock_cache():
    """Create a mock cache manager."""
    return Mock()


def test_client_init_with_settings():
    """Test client initialization with provided settings."""
    settings = ClientSettings(cache_dir="/custom/cache")

    with patch("asxshorts.client.CacheManager") as mock_cache_class:
        with patch("asxshorts.client.DefaultResolver") as mock_resolver_class:
            client = ShortsClient(settings=settings)

            assert client.settings == settings
            mock_cache_class.assert_called_once_with("/custom/cache")


def test_client_init_with_kwargs():
    """Test client initialization with kwargs."""
    with patch("asxshorts.client.CacheManager") as mock_cache_class:
        with patch("asxshorts.client.DefaultResolver") as mock_resolver_class:
            client = ShortsClient(cache_dir="/custom/cache", timeout=30.0)

            assert client.settings.cache_dir == "/custom/cache"
            assert client.settings.timeout == 30.0


def test_client_init_with_custom_session_and_resolver(mock_session, mock_resolver):
    """Test client initialization with custom session and resolver."""
    with patch("asxshorts.client.CacheManager"):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)

        assert client.session == mock_session
        assert client.resolver == mock_resolver


def test_configure_logging():
    """Library should not configure global logging."""
    with patch("logging.basicConfig") as mock_config:
        with patch("asxshorts.client.CacheManager"):
            with patch("asxshorts.client.DefaultResolver"):
                settings = ClientSettings(log_level="DEBUG", log_format="%(message)s")
                _ = ShortsClient(settings=settings)

                mock_config.assert_not_called()


def test_create_session():
    """Test session creation with retry configuration."""
    with patch("asxshorts.client.CacheManager"):
        with patch("asxshorts.client.DefaultResolver"):
            settings = ClientSettings(retries=5, backoff=1.0, user_agent="test-agent")
            client = ShortsClient(settings=settings)

            session = client.session
            assert "User-Agent" in session.headers
            assert session.headers["User-Agent"] == "test-agent"
            assert "Accept" in session.headers


def test_fetch_with_retry_rate_limit_error(mock_session, mock_resolver):
    """Test fetch with retry encountering rate limit error."""
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "30"}
    mock_session.get.return_value = mock_response

    with patch("asxshorts.client.CacheManager"):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)

        with pytest.raises(RateLimitError, match="Rate limited, retry after 30s"):
            client._fetch_with_retry("https://example.com/test.csv")


def test_fetch_with_retry_rate_limit_no_header(mock_session, mock_resolver):
    """Test fetch with retry encountering rate limit without Retry-After header."""
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.headers = {}
    mock_session.get.return_value = mock_response

    with patch("asxshorts.client.CacheManager"):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)

        with pytest.raises(RateLimitError, match="Rate limited, retry after 60s"):
            client._fetch_with_retry("https://example.com/test.csv")


def test_fetch_with_retry_request_exception(mock_session, mock_resolver):
    """Test fetch with retry encountering request exceptions."""
    mock_session.get.side_effect = [
        requests.exceptions.ConnectionError("Connection failed"),
        requests.exceptions.Timeout("Request timeout"),
        requests.exceptions.HTTPError("HTTP error"),
    ]

    with patch("asxshorts.client.CacheManager"):
        with patch("time.sleep"):  # Speed up test
            settings = ClientSettings(retries=2, backoff=0.1)
            client = ShortsClient(
                settings=settings, session=mock_session, resolver=mock_resolver
            )

            with pytest.raises(FetchError, match="Failed to fetch .* after 3 attempts"):
                client._fetch_with_retry("https://example.com/test.csv")


def test_fetch_with_retry_success_after_failure(mock_session, mock_resolver):
    """Test fetch with retry succeeding after initial failures."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"test,data\n1,2"
    mock_response.raise_for_status.return_value = None

    mock_session.get.side_effect = [
        requests.exceptions.ConnectionError("Connection failed"),
        mock_response,
    ]

    with patch("asxshorts.client.CacheManager"):
        with patch("time.sleep"):  # Speed up test
            settings = ClientSettings(retries=2, backoff=0.1)
            client = ShortsClient(
                settings=settings, session=mock_session, resolver=mock_resolver
            )

            result = client._fetch_with_retry("https://example.com/test.csv")
            assert result == b"test,data\n1,2"


def test_fetch_day_resolver_not_found_error(mock_session, mock_resolver):
    """Test fetch_day when resolver raises NotFoundError."""
    mock_resolver.url_for.side_effect = NotFoundError(date(2024, 1, 15))

    mock_cache = Mock()
    mock_cache.read_cached.return_value = None

    with patch("asxshorts.client.CacheManager", return_value=mock_cache):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)

        with pytest.raises(NotFoundError):
            client.fetch_day(date(2024, 1, 15))


def test_fetch_day_cache_write_failure(mock_session, mock_resolver):
    """Test fetch_day with cache write failure."""
    # Mock successful fetch
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"ASX Code,Company Name,Short Sold,Issued Shares,% Short\nCBA,Commonwealth Bank,1000,10000,10.0"
    mock_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_response

    # Mock cache that fails to write
    mock_cache = Mock()
    mock_cache.read_cached.return_value = None
    mock_cache.write_cached.side_effect = Exception("Cache write failed")

    with patch("asxshorts.client.CacheManager", return_value=mock_cache):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)

        # Should still succeed despite cache write failure
        result = client.fetch_day(date(2024, 1, 15))
        assert result.record_count == 1
        assert result.from_cache is False


def test_fetch_day_with_cached_data(mock_session, mock_resolver):
    """Test fetch_day using cached data."""
    cached_content = b"ASX Code,Company Name,Short Sold,Issued Shares,% Short\nCBA,Commonwealth Bank,1000,10000,10.0"

    mock_cache = Mock()
    mock_cache.read_cached.return_value = cached_content

    with patch("asxshorts.client.CacheManager", return_value=mock_cache):
        with patch("asxshorts.client.parse_csv_content") as mock_parse:
            with patch("asxshorts.client.validate_records") as mock_validate:
                mock_parse.return_value = [{"asx_code": "CBA"}]
                mock_validate.return_value = [
                    {
                        "report_date": date(2024, 1, 15),
                        "asx_code": "CBA",
                        "company_name": "Commonwealth Bank",
                        "short_sold": 1000,
                        "issued_shares": 10000,
                        "percent_short": 10.0,
                        "raw": {},
                    }
                ]

                client = ShortsClient(session=mock_session, resolver=mock_resolver)
                result = client.fetch_day(date(2024, 1, 15))

                assert result.from_cache is True
                assert result.record_count == 1
                # Should not call session.get when using cache
                mock_session.get.assert_not_called()


def test_fetch_range_start_after_end(mock_session, mock_resolver):
    """Test fetch_range with start_date > end_date."""
    with patch("asxshorts.client.CacheManager"):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)

        with pytest.raises(ValueError, match="start_date must be <= end_date"):
            client.fetch_range(date(2024, 1, 15), date(2024, 1, 10))


def test_fetch_range_with_failures(mock_session, mock_resolver):
    """Test fetch_range with some dates failing."""

    def mock_fetch_day(d, force=False):
        if d == date(2024, 1, 11):
            raise NotFoundError(date(2024, 1, 11))
        elif d == date(2024, 1, 12):
            raise Exception("Unexpected error")
        else:
            return FetchResult(
                fetch_date=d,
                record_count=1,
                from_cache=False,
                fetch_time_ms=0.0,
                url="https://example.com/test.csv",
                records=[
                    ShortRecord(
                        report_date=d,
                        asx_code="CBA",
                        company_name="Test Company",
                        short_sold=1000,
                        issued_shares=10000,
                        percent_short=10.0,
                        raw={},
                    )
                ],
            )

    with patch("asxshorts.client.CacheManager"):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)

        with patch.object(client, "fetch_day", side_effect=mock_fetch_day):
            result = client.fetch_range(date(2024, 1, 10), date(2024, 1, 12))

            assert len(result.successful_dates) == 1
            assert len(result.failed_dates) == 2
            assert result.total_records == 1
            assert date(2024, 1, 11) in result.failed_dates
            assert date(2024, 1, 12) in result.failed_dates


def test_cleanup_cache_with_old_files(mock_session, mock_resolver):
    """Test cleanup_cache removing old files."""
    # Create mock cache directory with files
    mock_cache_dir = Mock()
    mock_old_file = Mock()
    mock_old_file.stat.return_value.st_mtime = time.time() - (
        40 * 24 * 3600
    )  # 40 days old
    mock_new_file = Mock()
    mock_new_file.stat.return_value.st_mtime = time.time() - (
        10 * 24 * 3600
    )  # 10 days old

    mock_cache_dir.glob.return_value = [mock_old_file, mock_new_file]

    mock_cache = Mock()
    mock_cache.cache_dir = mock_cache_dir

    with patch("asxshorts.client.CacheManager", return_value=mock_cache):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)
        client.cleanup_cache(max_age_days=30)

        # Should remove old file but not new file
        mock_old_file.unlink.assert_called_once()
        mock_new_file.unlink.assert_not_called()
        mock_cache.cleanup_stale_locks.assert_called_once()


def test_cleanup_cache_unlink_error(mock_session, mock_resolver):
    """Test cleanup_cache handling unlink errors."""
    # Create mock cache directory with file that fails to unlink
    mock_cache_dir = Mock()
    mock_old_file = Mock()
    mock_old_file.stat.return_value.st_mtime = time.time() - (
        40 * 24 * 3600
    )  # 40 days old
    mock_old_file.unlink.side_effect = OSError("Permission denied")

    mock_cache_dir.glob.return_value = [mock_old_file]

    mock_cache = Mock()
    mock_cache.cache_dir = mock_cache_dir

    with patch("asxshorts.client.CacheManager", return_value=mock_cache):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)

        # Should not raise exception despite unlink error
        client.cleanup_cache(max_age_days=30)
        mock_old_file.unlink.assert_called_once()


def test_context_manager(mock_session, mock_resolver):
    """Test client as context manager."""
    with patch("asxshorts.client.CacheManager"):
        with ShortsClient(session=mock_session, resolver=mock_resolver) as client:
            assert client is not None

        # Should close session on exit
        mock_session.close.assert_called_once()


def test_context_manager_session_without_close(mock_resolver):
    """Test context manager with session that doesn't have close method."""
    mock_session = Mock()
    del mock_session.close  # Remove close method

    with patch("asxshorts.client.CacheManager"):
        with ShortsClient(session=mock_session, resolver=mock_resolver) as client:
            assert client is not None
        # Should not raise error even if session doesn't have close


def test_cache_stats(mock_session, mock_resolver):
    """Test cache_stats method."""
    mock_cache = Mock()
    mock_cache.cache_stats.return_value = {
        "count": 5,
        "size_bytes": 1024,
        "path": "/test/cache",
    }

    with patch("asxshorts.client.CacheManager", return_value=mock_cache):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)
        stats = client.cache_stats()

        assert stats.count == 5
        assert stats.size_bytes == 1024
        assert stats.path == "/test/cache"


def test_clear_cache(mock_session, mock_resolver):
    """Test clear_cache method."""
    mock_cache = Mock()

    with patch("asxshorts.client.CacheManager", return_value=mock_cache):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)
        client.clear_cache()

        mock_cache.clear_cache.assert_called_once()


def test_session_retry_configuration():
    """Test that session is configured with proper retry strategy."""
    with patch("asxshorts.client.CacheManager"):
        with patch("asxshorts.client.DefaultResolver"):
            settings = ClientSettings(retries=3, backoff=0.5)

            with patch("requests.Session") as mock_session_class:
                with patch("asxshorts.client.HTTPAdapter") as mock_adapter_class:
                    with patch("asxshorts.client.Retry") as mock_retry_class:
                        mock_session = Mock()
                        mock_session_class.return_value = mock_session

                        client = ShortsClient(settings=settings)

                        # Verify retry strategy was created with correct parameters
                        mock_retry_class.assert_called_once_with(
                            total=3,
                            status_forcelist=[429, 500, 502, 503, 504],
                            backoff_factor=0.5,
                            allowed_methods=["HEAD", "GET", "OPTIONS"],
                        )

                        # Verify adapter was created and mounted
                        mock_adapter_class.assert_called_once()
                        assert mock_session.mount.call_count == 2


def test_create_session_without_http_adapter_retry():
    """Session can disable adapter-level retries via settings."""
    with patch("asxshorts.client.CacheManager"):
        with patch("asxshorts.client.DefaultResolver"):
            settings = ClientSettings(
                retries=3, backoff=0.5, http_adapter_retries=False
            )

            with patch("requests.Session") as mock_session_class:
                with patch("asxshorts.client.HTTPAdapter") as mock_adapter_class:
                    with patch("asxshorts.client.Retry") as mock_retry_class:
                        mock_session = Mock()
                        mock_session_class.return_value = mock_session

                        _ = ShortsClient(settings=settings)

                        # Retry() should not be constructed when disabled
                        mock_retry_class.assert_not_called()
                        # HTTPAdapter should be created with max_retries=0
                        assert mock_adapter_class.call_count == 1
                        kwargs = mock_adapter_class.call_args.kwargs
                        assert kwargs.get("max_retries") == 0
                        assert mock_session.mount.call_count == 2


def test_fetch_with_retry_http_error_response(mock_session, mock_resolver):
    """Test fetch with retry when response raises HTTP error."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found"
    )
    mock_session.get.return_value = mock_response

    with patch("asxshorts.client.CacheManager"):
        with patch("time.sleep"):  # Speed up test
            settings = ClientSettings(retries=1, backoff=0.1)
            client = ShortsClient(
                settings=settings, session=mock_session, resolver=mock_resolver
            )

            with pytest.raises(FetchError, match="Failed to fetch .* after 2 attempts"):
                client._fetch_with_retry("https://example.com/test.csv")


def test_fetch_day_force_bypass_cache(mock_session, mock_resolver):
    """Test fetch_day with force=True bypasses cache."""
    # Mock successful fetch
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"ASX Code,Company Name,Short Sold,Issued Shares,% Short\nCBA,Commonwealth Bank,1000,10000,10.0"
    mock_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_response

    # Mock cache with data
    mock_cache = Mock()
    mock_cache.read_cached.return_value = b"cached data"

    with patch("asxshorts.client.CacheManager", return_value=mock_cache):
        client = ShortsClient(session=mock_session, resolver=mock_resolver)

        result = client.fetch_day(date(2024, 1, 15), force=True)

        # Should not read from cache when force=True
        mock_cache.read_cached.assert_not_called()
        # Should fetch from network
        mock_session.get.assert_called_once()
        assert result.from_cache is False

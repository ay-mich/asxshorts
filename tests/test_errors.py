"""Tests for custom exception classes."""

from datetime import date

from asxshorts.errors import (
    CacheError,
    FetchError,
    NotFoundError,
    ParseError,
    RateLimitError,
)


class TestFetchError:
    """Test cases for FetchError base exception."""

    def test_init_message_only(self):
        """Test initialization with message only."""
        error = FetchError("Test error message")
        assert str(error) == "Test error message"
        assert error.date_requested is None
        assert error.url is None

    def test_init_with_date(self):
        """Test initialization with date."""
        test_date = date(2023, 12, 15)
        error = FetchError("Test error", date_requested=test_date)
        assert str(error) == "Test error"
        assert error.date_requested == test_date
        assert error.url is None

    def test_init_with_url(self):
        """Test initialization with URL."""
        test_url = "https://example.com/data.csv"
        error = FetchError("Test error", url=test_url)
        assert str(error) == "Test error"
        assert error.date_requested is None
        assert error.url == test_url

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        test_date = date(2023, 12, 15)
        test_url = "https://example.com/data.csv"
        error = FetchError("Test error", date_requested=test_date, url=test_url)
        assert str(error) == "Test error"
        assert error.date_requested == test_date
        assert error.url == test_url

    def test_inheritance(self):
        """Test that FetchError inherits from Exception."""
        error = FetchError("Test error")
        assert isinstance(error, Exception)


class TestNotFoundError:
    """Test cases for NotFoundError."""

    def test_init_date_only(self):
        """Test initialization with date only."""
        test_date = date(2023, 12, 15)
        error = NotFoundError(test_date)
        expected_message = "No data found for date 2023-12-15"
        assert str(error) == expected_message
        assert error.date_requested == test_date
        assert error.url is None

    def test_init_with_url(self):
        """Test initialization with date and URL."""
        test_date = date(2023, 12, 15)
        test_url = "https://example.com/data.csv"
        error = NotFoundError(test_date, url=test_url)
        expected_message = (
            "No data found for date 2023-12-15 at URL: https://example.com/data.csv"
        )
        assert str(error) == expected_message
        assert error.date_requested == test_date
        assert error.url == test_url

    def test_inheritance(self):
        """Test that NotFoundError inherits from FetchError."""
        test_date = date(2023, 12, 15)
        error = NotFoundError(test_date)
        assert isinstance(error, FetchError)
        assert isinstance(error, Exception)

    def test_date_formatting(self):
        """Test date formatting in error message."""
        # Test different date formats
        test_cases = [
            (date(2023, 1, 1), "2023-01-01"),
            (date(2023, 12, 31), "2023-12-31"),
            (date(2000, 2, 29), "2000-02-29"),  # Leap year
        ]

        for test_date, expected_date_str in test_cases:
            error = NotFoundError(test_date)
            expected_message = f"No data found for date {expected_date_str}"
            assert str(error) == expected_message


class TestRateLimitError:
    """Test cases for RateLimitError."""

    def test_init_default(self):
        """Test initialization with default message."""
        error = RateLimitError()
        assert str(error) == "Rate limit exceeded"
        assert error.retry_after is None
        assert error.date_requested is None
        assert error.url is None

    def test_init_custom_message(self):
        """Test initialization with custom message."""
        custom_message = "API rate limit exceeded"
        error = RateLimitError(custom_message)
        assert str(error) == custom_message
        assert error.retry_after is None

    def test_init_with_retry_after(self):
        """Test initialization with retry_after parameter."""
        retry_seconds = 60
        error = RateLimitError(retry_after=retry_seconds)
        assert str(error) == "Rate limit exceeded"
        assert error.retry_after == retry_seconds

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        custom_message = "Too many requests"
        retry_seconds = 120
        error = RateLimitError(custom_message, retry_after=retry_seconds)
        assert str(error) == custom_message
        assert error.retry_after == retry_seconds

    def test_inheritance(self):
        """Test that RateLimitError inherits from FetchError."""
        error = RateLimitError()
        assert isinstance(error, FetchError)
        assert isinstance(error, Exception)


class TestParseError:
    """Test cases for ParseError."""

    def test_init_message_only(self):
        """Test initialization with message only."""
        error = ParseError("CSV parsing failed")
        assert str(error) == "CSV parsing failed"
        assert error.date_requested is None
        assert error.details is None
        assert error.url is None

    def test_init_with_date(self):
        """Test initialization with date."""
        test_date = date(2023, 12, 15)
        error = ParseError("CSV parsing failed", date_requested=test_date)
        assert str(error) == "CSV parsing failed"
        assert error.date_requested == test_date
        assert error.details is None

    def test_init_with_details(self):
        """Test initialization with details."""
        details = "Invalid column format"
        error = ParseError("CSV parsing failed", details=details)
        expected_message = "CSV parsing failed Details: Invalid column format"
        assert str(error) == expected_message
        assert error.details == details
        assert error.date_requested is None

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        test_date = date(2023, 12, 15)
        details = "Missing required columns"
        error = ParseError(
            "CSV parsing failed", date_requested=test_date, details=details
        )
        expected_message = "CSV parsing failed Details: Missing required columns"
        assert str(error) == expected_message
        assert error.date_requested == test_date
        assert error.details == details

    def test_inheritance(self):
        """Test that ParseError inherits from FetchError."""
        error = ParseError("CSV parsing failed")
        assert isinstance(error, FetchError)
        assert isinstance(error, Exception)

    def test_details_formatting(self):
        """Test details formatting in error message."""
        test_cases = [
            ("Simple error", "Base message Details: Simple error"),
            ("Error with\nnewlines", "Base message Details: Error with\nnewlines"),
            ("", "Base message"),  # Empty details should not add Details:
        ]

        for details, expected_message in test_cases:
            error = ParseError("Base message", details=details)
            assert str(error) == expected_message


class TestCacheError:
    """Test cases for CacheError."""

    def test_init_message_only(self):
        """Test initialization with message only."""
        error = CacheError("Cache operation failed")
        assert str(error) == "Cache operation failed"
        assert error.cache_path is None
        assert error.date_requested is None
        assert error.url is None

    def test_init_with_cache_path(self):
        """Test initialization with cache path."""
        cache_path = "/tmp/cache/data.json"
        error = CacheError("Cache write failed", cache_path=cache_path)
        assert str(error) == "Cache write failed"
        assert error.cache_path == cache_path

    def test_inheritance(self):
        """Test that CacheError inherits from FetchError."""
        error = CacheError("Cache operation failed")
        assert isinstance(error, FetchError)
        assert isinstance(error, Exception)

    def test_cache_path_types(self):
        """Test different cache path types."""
        test_cases = [
            "/absolute/path/to/cache.json",
            "relative/path/cache.json",
            "cache.json",
            "",  # Empty path
        ]

        for cache_path in test_cases:
            error = CacheError("Cache operation failed", cache_path=cache_path)
            assert str(error) == "Cache operation failed"
            assert error.cache_path == cache_path

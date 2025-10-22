"""Custom exceptions for asxshorts package."""

from datetime import date


class FetchError(Exception):
    """Base exception for fetch operations."""

    def __init__(
        self,
        message: str,
        date_requested: date | None = None,
        url: str | None = None,
    ):
        """Initialize FetchError.

        Args:
            message: Error message.
            date_requested: Date that was being fetched when error occurred.
            url: URL that was being accessed when error occurred.
        """
        super().__init__(message)
        self.date_requested = date_requested
        self.url = url


class NotFoundError(FetchError):
    """Data not found for specified date."""

    def __init__(self, date_requested: date, url: str | None = None):
        """Initialize NotFoundError.

        Args:
            date_requested: Date for which data was not found.
            url: URL that was checked for data.
        """
        message = f"No data found for date {date_requested.strftime('%Y-%m-%d')}"
        if url:
            message += f" at URL: {url}"
        super().__init__(message, date_requested, url)


class RateLimitError(FetchError):
    """Rate limit exceeded."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int | None = None
    ):
        """Initialize RateLimitError.

        Args:
            message: Error message.
            retry_after: Number of seconds to wait before retrying.
        """
        super().__init__(message)
        self.retry_after = retry_after


class ParseError(FetchError):
    """CSV parsing failed."""

    def __init__(
        self,
        message: str,
        date_requested: date | None = None,
        details: str | None = None,
    ):
        """Initialize ParseError.

        Args:
            message: Error message.
            date_requested: Date being parsed when error occurred.
            details: Additional error details.
        """
        full_message = message
        if details:
            full_message += f" Details: {details}"
        super().__init__(full_message, date_requested)
        self.details = details


class CacheError(FetchError):
    """Cache operation failed."""

    def __init__(self, message: str, cache_path: str | None = None):
        """Initialize CacheError.

        Args:
            message: Error message.
            cache_path: Path to cache file that caused the error.
        """
        super().__init__(message)
        self.cache_path = cache_path

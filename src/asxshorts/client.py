"""Main ShortsClient for fetching ASX short selling data."""

import logging
import time
from datetime import date, timedelta
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache import CacheManager
from .errors import FetchError, NotFoundError, RateLimitError
from .models import CacheStats, ClientSettings, FetchResult, RangeResult, ShortRecord
from .parse import parse_csv_content, validate_records

# Expose DefaultResolver symbol for tests that patch it, even though
# the client uses CompositeResolver by default.
from .resolve import (
    CompositeResolver,
    DefaultResolver,
    UrlResolver,
)

logger = logging.getLogger(__name__)


class ShortsClient:
    """Client for fetching ASX short selling data with caching."""

    def __init__(
        self,
        *,
        settings: ClientSettings | None = None,
        session: requests.Session | None = None,
        resolver: UrlResolver | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the ShortsClient.

        Args:
            settings: Client settings (will be created from kwargs if not provided)
            session: Custom requests session
            resolver: Custom URL resolver
            **kwargs: Settings passed to ClientSettings if settings not provided
        """
        # Initialize settings
        if settings is None:
            self.settings = ClientSettings(**kwargs)
        else:
            self.settings = settings

        # Initialize components
        self.cache = CacheManager(self.settings.cache_dir)
        self.session = session or self._create_session()
        if resolver is not None:
            self.resolver = resolver
        else:
            # Prefer ASIC JSON-based resolution with DefaultResolver fallback
            self.resolver = CompositeResolver(self.settings.base_url, self.session)

        logger.debug(
            f"Initialized ShortsClient with cache_dir={self.settings.cache_dir}, base_url={self.settings.base_url}"
        )

    # Intentionally avoid configuring global logging in a library.
    # The CLI configures logging; library users can configure as desired.

    def _create_session(self) -> requests.Session:
        """Create configured requests session with retry logic."""
        session = requests.Session()

        # Set headers
        session.headers.update(
            {
                "User-Agent": self.settings.user_agent,
                "Accept": "text/csv,text/plain,*/*",
                "Accept-Encoding": "gzip, deflate",
            }
        )

        # Configure retry strategy
        if self.settings.http_adapter_retries:
            retry_strategy = Retry(
                total=self.settings.retries,
                status_forcelist=[429, 500, 502, 503, 504],
                backoff_factor=self.settings.backoff,
                allowed_methods=["HEAD", "GET", "OPTIONS"],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
        else:
            # Disable adapter-level retries to avoid double backoff when using
            # the client's explicit retry loop in _fetch_with_retry.
            adapter = HTTPAdapter(max_retries=0)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _fetch_with_retry(self, url: str) -> bytes:
        """Fetch URL content with exponential backoff retry."""
        last_exception = None

        for attempt in range(self.settings.retries + 1):
            try:
                logger.debug(f"Fetching {url} (attempt {attempt + 1})")

                response = self.session.get(url, timeout=self.settings.timeout)

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError(
                        f"Rate limited, retry after {retry_after}s", retry_after
                    )

                response.raise_for_status()

                logger.debug(
                    f"Successfully fetched {url} ({len(response.content)} bytes)"
                )
                return response.content

            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.settings.retries:
                    sleep_time = self.settings.backoff * (2**attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}): {e}. Retrying in {sleep_time}s"
                    )
                    time.sleep(sleep_time)
                else:
                    logger.error(f"All retry attempts failed for {url}")

        raise FetchError(
            f"Failed to fetch {url} after {self.settings.retries + 1} attempts: {last_exception}"
        )

    def fetch_day(self, d: date, *, force: bool = False) -> FetchResult:
        """Fetch short selling data for a single day.

        Args:
            d: Date to fetch data for
            force: If True, bypass cache and fetch fresh data

        Returns:
            FetchResult containing the data and metadata

        Raises:
            NotFoundError: If data is not available for the date
            FetchError: If there's an error fetching the data
        """
        logger.info(f"Fetching short selling data for {d}")
        start_time = time.perf_counter()

        # Check cache first (unless forced)
        if not force:
            cached_content = self.cache.read_cached(d)
            if cached_content:
                logger.debug(f"Using cached data for {d}")
                records = parse_csv_content(cached_content, d)
                validated_records = validate_records(records, d)
                # Convert dict records to Pydantic models
                record_models = [ShortRecord(**record) for record in validated_records]
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return FetchResult(
                    fetch_date=d,
                    record_count=len(record_models),
                    from_cache=True,
                    fetch_time_ms=elapsed_ms,
                    url=None,
                    records=record_models,
                )

        # Resolve URL for the date
        try:
            url = self.resolver.url_for(d)
        except NotFoundError:
            logger.warning(f"No URL found for {d}")
            raise

        # Fetch content
        content = self._fetch_with_retry(url)

        # Parse content
        records = parse_csv_content(content, d)
        validated_records = validate_records(records, d)

        # Convert to Pydantic models
        record_models = [ShortRecord(**record) for record in validated_records]

        # Cache the raw content
        try:
            self.cache.write_cached(d, content)
        except Exception as e:
            logger.warning(f"Failed to cache data for {d}: {e}")

        logger.info(f"Successfully fetched {len(record_models)} records for {d}")
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return FetchResult(
            fetch_date=d,
            record_count=len(record_models),
            from_cache=False,
            fetch_time_ms=elapsed_ms,
            url=url,
            records=record_models,
        )

    def fetch_range(
        self, start_date: date, end_date: date, *, force: bool = False
    ) -> RangeResult:
        """Fetch short selling data for a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            force: If True, bypass cache and fetch fresh data

        Returns:
            RangeResult containing the data and metadata

        Raises:
            ValueError: If start_date > end_date
            FetchError: If there's an error fetching data
        """
        if start_date > end_date:
            raise ValueError("start_date must be <= end_date")

        logger.info(f"Fetching short selling data from {start_date} to {end_date}")
        overall_start = time.perf_counter()

        results = {}
        failed_dates = []
        current_date = start_date

        while current_date <= end_date:
            try:
                fetch_result = self.fetch_day(current_date, force=force)
                results[current_date] = fetch_result
            except NotFoundError:
                logger.warning(f"No data available for {current_date}")
                failed_dates.append(current_date)
            except Exception as e:
                logger.error(f"Failed to fetch data for {current_date}: {e}")
                failed_dates.append(current_date)

            current_date += timedelta(days=1)

        total_records = sum(result.record_count for result in results.values())
        logger.info(
            f"Successfully fetched data for {len(results)} dates with {total_records} total records"
        )

        total_elapsed_ms = (time.perf_counter() - overall_start) * 1000.0
        return RangeResult(
            start_date=start_date,
            end_date=end_date,
            total_records=total_records,
            successful_dates=list(results.keys()),
            failed_dates=failed_dates,
            total_fetch_time_ms=total_elapsed_ms,
            results=results,
        )

    def clear_cache(self) -> None:
        """Clear all cached files."""
        logger.info("Clearing cache")
        self.cache.clear_cache()

    def cache_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats object with cache information
        """
        stats = self.cache.cache_stats()
        return CacheStats(**stats)

    def cleanup_cache(self, max_age_days: int = 30) -> None:
        """Remove cached files older than max_age_days."""
        logger.info(f"Cleaning up cache files older than {max_age_days} days")

        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        cache_dir = self.cache.cache_dir

        removed_count = 0
        for cache_file in cache_dir.glob("*.csv"):
            if cache_file.stat().st_mtime < cutoff_time:
                try:
                    cache_file.unlink()
                    removed_count += 1
                    logger.debug(f"Removed old cache file: {cache_file}")
                except OSError as e:
                    logger.warning(f"Failed to remove {cache_file}: {e}")

        logger.info(f"Removed {removed_count} old cache files")

        # Also cleanup stale locks
        self.cache.cleanup_stale_locks()

    def __enter__(self) -> "ShortsClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - cleanup resources."""
        if hasattr(self.session, "close"):
            self.session.close()

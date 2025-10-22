"""File cache utilities with locking and atomic operations."""

import contextlib
import logging
import os
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any

from .errors import CacheError

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages local file cache with atomic operations and file locking."""

    def __init__(self, cache_dir: str):
        """Initialize the CacheManager.

        Args:
            cache_dir: Directory path for storing cache files.
        """
        self.cache_dir = Path(cache_dir).expanduser().resolve()
        self.locks_dir = self.cache_dir / ".locks"
        # Lazy-create directories on first write/lock to avoid empty dirs

    def _get_cache_path(self, d: date) -> Path:
        """Get cache file path for a given date."""
        filename = f"{d.strftime('%Y-%m-%d')}.csv"
        return self.cache_dir / filename

    def _get_lock_path(self, d: date) -> Path:
        """Get lock file path for a given date."""
        filename = f"{d.strftime('%Y-%m-%d')}.csv.lock"
        return self.locks_dir / filename

    def _acquire_lock(self, d: date, timeout: float = 30.0) -> bool:
        """Acquire file lock for atomic operations."""
        # Ensure lock directory exists lazily
        try:
            self.locks_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Failed to create locks directory: {e}")
        lock_path = self._get_lock_path(d)
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Try to create lock file exclusively
                with Path(lock_path).open("x") as f:
                    f.write(str(os.getpid()))
                logger.debug(f"Acquired lock for {d}")
                return True
            except FileExistsError:
                # Lock exists, wait a bit
                time.sleep(0.1)

        logger.warning(f"Failed to acquire lock for {d} within {timeout}s")
        return False

    def _release_lock(self, d: date) -> None:
        """Release file lock."""
        lock_path = self._get_lock_path(d)
        try:
            lock_path.unlink(missing_ok=True)
            logger.debug(f"Released lock for {d}")
        except OSError as e:
            logger.warning(f"Failed to release lock for {d}: {e}")

    def has_cached(self, d: date) -> bool:
        """Check if data for date is cached."""
        cache_path = self._get_cache_path(d)
        return cache_path.exists() and cache_path.stat().st_size > 0

    def read_cached(self, d: date) -> bytes | None:
        """Read cached data for date."""
        if not self.has_cached(d):
            return None

        cache_path = self._get_cache_path(d)
        try:
            with cache_path.open("rb") as f:
                content = f.read()
            logger.debug(f"Cache hit for {d}")
            return content
        except OSError as e:
            logger.warning(f"Failed to read cache for {d}: {e}")
            return None

    def write_cached(self, d: date, content: bytes) -> None:
        """Write data to cache atomically."""
        # Ensure cache directory exists lazily
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise CacheError(
                f"Failed to create cache directory: {e}", str(self.cache_dir)
            ) from e
        if not self._acquire_lock(d):
            raise CacheError(f"Failed to acquire lock for caching {d}")

        try:
            cache_path = self._get_cache_path(d)

            # Write to temporary file first, then move atomically
            with tempfile.NamedTemporaryFile(
                dir=self.cache_dir, delete=False, suffix=".tmp"
            ) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name

            # Atomic move
            Path(tmp_path).rename(cache_path)
            logger.debug(f"Cached data for {d} ({len(content)} bytes)")

        except OSError as e:
            # Clean up temp file if it exists
            if "tmp_path" in locals():
                with contextlib.suppress(OSError):
                    Path(tmp_path).unlink()
            raise CacheError(f"Failed to write cache for {d}: {e}") from e
        finally:
            self._release_lock(d)

    def clear_cache(self) -> None:
        """Remove all cached files."""
        try:
            if not self.cache_dir.exists():
                return
            for cache_file in self.cache_dir.glob("*.csv"):
                cache_file.unlink()
            logger.info("Cache cleared")
        except OSError as e:
            raise CacheError(f"Failed to clear cache: {e}") from e

    def cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        try:
            if not self.cache_dir.exists():
                return {
                    "count": 0,
                    "size_bytes": 0,
                    "path": str(self.cache_dir),
                    "oldest_file": None,
                    "newest_file": None,
                }
            csv_files = list(self.cache_dir.glob("*.csv"))
            total_size = sum(f.stat().st_size for f in csv_files if f.is_file())
            # Derive oldest/newest from filenames if possible (YYYY-MM-DD.csv)
            oldest_date = None
            newest_date = None
            for f in csv_files:
                try:
                    name = f.stem  # 'YYYY-MM-DD'
                    year, month, day = name.split("-")
                    from datetime import date as _date

                    d = _date(int(year), int(month), int(day))
                    if oldest_date is None or d < oldest_date:
                        oldest_date = d
                    if newest_date is None or d > newest_date:
                        newest_date = d
                except (ValueError, TypeError, IndexError):
                    # Ignore files that don't match expected pattern
                    # ValueError: invalid date values or int() conversion
                    # TypeError: unexpected type for int() conversion
                    # IndexError: not enough parts when splitting filename
                    continue

            return {
                "count": len(csv_files),
                "size_bytes": total_size,
                "path": str(self.cache_dir),
                "oldest_file": oldest_date,
                "newest_file": newest_date,
            }
        except OSError as e:
            raise CacheError(f"Failed to get cache stats: {e}") from e

    def cleanup_stale_locks(self, max_age_seconds: int = 3600) -> None:
        """Remove stale lock files older than max_age_seconds."""
        try:
            if not self.locks_dir.exists():
                return
            current_time = time.time()
            for lock_file in self.locks_dir.glob("*.lock"):
                if current_time - lock_file.stat().st_mtime > max_age_seconds:
                    lock_file.unlink(missing_ok=True)
                    logger.debug(f"Removed stale lock: {lock_file}")
        except OSError as e:
            logger.warning(f"Failed to cleanup stale locks: {e}")

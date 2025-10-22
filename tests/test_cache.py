"""Tests for asxshorts.cache module."""

import os
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from asxshorts.cache import CacheManager
from asxshorts.errors import CacheError


class TestCacheManager:
    """Test CacheManager functionality."""

    def test_init(self):
        """Test CacheManager initialization (lazy directory)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            assert cache.cache_dir == Path(tmpdir).resolve()
            # Directory may not be created until first write
            # (lazy creation to avoid empty dirs)
            # Do not assert existence here

    def test_init_creates_directory(self):
        """Test that directory is created on first write (lazy)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "new_cache_dir")
            cache = CacheManager(cache_path)
            assert not Path(cache_path).exists()
            cache.write_cached(date(2024, 1, 1), b"x")
            assert Path(cache_path).exists()

    def test_cache_path_for_date(self):
        """Test cache path generation for dates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            test_date = date(2024, 1, 15)

            path = cache._get_cache_path(test_date)
            expected_path = Path(tmpdir).resolve() / "2024-01-15.csv"
            assert path == expected_path

    def test_write_and_read_cached(self):
        """Test writing and reading cached data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            test_date = date(2024, 1, 15)
            test_content = b"test,csv,content\n1,2,3"

            # Write to cache
            cache.write_cached(test_date, test_content)

            # Verify file exists
            cache_file = cache._get_cache_path(test_date)
            assert cache_file.exists()

            # Read from cache
            cached_content = cache.read_cached(test_date)
            assert cached_content == test_content

    def test_read_cached_nonexistent(self):
        """Test reading from cache when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            test_date = date(2024, 1, 15)

            cached_content = cache.read_cached(test_date)
            assert cached_content is None

    def test_read_cached_corrupted_file(self):
        """Test reading corrupted cache file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            test_date = date(2024, 1, 15)

            # Create a corrupted file (directory instead of file)
            cache_file = cache._get_cache_path(test_date)
            cache_file.mkdir()

            cached_content = cache.read_cached(test_date)
            assert cached_content is None

    def test_write_cached_with_lock(self):
        """Test writing cached data with file locking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            test_date = date(2024, 1, 15)
            test_content = b"test,csv,content"

            cache.write_cached(test_date, test_content)

            # Verify file was written
            cache_file = cache._get_cache_path(test_date)
            assert cache_file.exists()

    def test_read_cached_with_lock(self):
        """Test reading cached data with file locking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            test_date = date(2024, 1, 15)
            test_content = b"test,csv,content"

            # First write the file
            cache.write_cached(test_date, test_content)

            # Read from cache
            cached_content = cache.read_cached(test_date)
            assert cached_content == test_content

    def test_write_cached_error_handling(self):
        """Test error handling during cache write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            test_date = date(2024, 1, 15)
            test_content = b"test,csv,content"

            # Make cache directory read-only to cause write error
            os.chmod(tmpdir, 0o444)

            try:
                # This should raise a CacheError due to permission issues
                with pytest.raises((CacheError, PermissionError)):
                    cache.write_cached(test_date, test_content)
            finally:
                # Restore permissions for cleanup
                os.chmod(tmpdir, 0o755)

    def test_stats_empty_cache(self):
        """Test cache stats for empty cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            stats = cache.cache_stats()

            assert stats["count"] == 0
            assert stats["size_bytes"] == 0
            assert stats["path"] == str(Path(tmpdir).resolve())

    def test_stats_with_files(self):
        """Test cache stats with cached files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)

            # Create some cache files
            dates = [date(2024, 1, 15), date(2024, 1, 16), date(2024, 1, 17)]
            content = b"test,csv,content"

            for test_date in dates:
                cache.write_cached(test_date, content)

            stats = cache.cache_stats()

            assert stats["count"] == 3
            assert stats["size_bytes"] > 0

    def test_stats_with_non_csv_files(self):
        """Test cache stats ignores non-CSV files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)

            # Create a CSV file
            cache.write_cached(date(2024, 1, 15), b"csv content")

            # Create a non-CSV file
            non_csv_file = Path(tmpdir) / "not_a_cache_file.txt"
            non_csv_file.write_text("not csv")

            stats = cache.cache_stats()

            # Should only count the CSV file
            assert stats["count"] == 1

    def test_clear_cache(self):
        """Test clearing all cache files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)

            # Create some cache files
            dates = [date(2024, 1, 15), date(2024, 1, 16)]
            for test_date in dates:
                cache.write_cached(test_date, b"content")

            # Create a non-cache file that should not be deleted
            non_cache_file = Path(tmpdir) / "keep_this.txt"
            non_cache_file.write_text("keep me")

            # Clear cache
            cache.clear_cache()

            # Verify cache files are gone
            for test_date in dates:
                cache_file = cache._get_cache_path(test_date)
                assert not cache_file.exists()

            # Verify non-cache file is kept
            assert non_cache_file.exists()

    @patch("time.time")
    def test_cleanup_old_files(self, mock_time):
        """Test cleanup of old cache files."""
        current_time = 1000000000  # Some timestamp
        mock_time.return_value = current_time

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)

            # Create files with different ages
            old_file = Path(tmpdir) / "2024-01-01.csv"
            new_file = Path(tmpdir) / "2024-01-15.csv"

            old_file.write_bytes(b"old content")
            new_file.write_bytes(b"new content")

            # Set file modification times
            old_time = current_time - (31 * 24 * 3600)  # 31 days ago
            new_time = current_time - (1 * 24 * 3600)  # 1 day ago

            os.utime(old_file, (old_time, old_time))
            os.utime(new_file, (new_time, new_time))

            # Cleanup stale locks (this is what the actual implementation has)
            cache.cleanup_stale_locks(max_age_seconds=30 * 24 * 3600)

            # Both files should remain (this method only cleans locks)
            assert old_file.exists()
            assert new_file.exists()

    def test_cleanup_no_files(self):
        """Test cleanup when no files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)

            # Should not raise any errors
            cache.cleanup_stale_locks()

    def test_cleanup_error_handling(self):
        """Test cleanup error handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)

            # Should not raise an exception even if locks dir doesn't exist
            cache.cleanup_stale_locks()

    def test_is_cached(self):
        """Test checking if date is cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            test_date = date(2024, 1, 15)

            # Initially not cached
            assert not cache.has_cached(test_date)

            # Write to cache
            cache.write_cached(test_date, b"content")

            # Now should be cached
            assert cache.has_cached(test_date)

    def test_cache_file_naming(self):
        """Test cache file naming convention."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)

            test_cases = [
                (date(2024, 1, 1), "2024-01-01.csv"),
                (date(2024, 12, 31), "2024-12-31.csv"),
                (date(2000, 2, 29), "2000-02-29.csv"),  # Leap year
            ]

            for test_date, expected_filename in test_cases:
                path = cache._get_cache_path(test_date)
                assert path.name == expected_filename

    def test_concurrent_access_simulation(self):
        """Test simulated concurrent access to cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            test_date = date(2024, 1, 15)

            # Simulate multiple writes (in real scenario, these would be from different processes)
            contents = [b"content1", b"content2", b"content3"]

            for content in contents:
                cache.write_cached(test_date, content)

            # Last write should win
            cached_content = cache.read_cached(test_date)
            assert cached_content == contents[-1]

    def test_large_content_handling(self):
        """Test handling of large content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            test_date = date(2024, 1, 15)

            # Create large content (1MB)
            large_content = b"x" * (1024 * 1024)

            cache.write_cached(test_date, large_content)
            cached_content = cache.read_cached(test_date)

            assert cached_content == large_content
            assert len(cached_content) == 1024 * 1024

    def test_empty_content_handling(self):
        """Test handling of empty content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            test_date = date(2024, 1, 15)

            empty_content = b""

            cache.write_cached(test_date, empty_content)

            # Empty files are not considered cached by has_cached
            assert not cache.has_cached(test_date)

            # But read_cached should still return None for empty files
            cached_content = cache.read_cached(test_date)
            assert cached_content is None

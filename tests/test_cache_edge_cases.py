"""Edge case tests for cache.py to improve coverage."""

import os
import tempfile
import time
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from asxshorts.cache import CacheManager
from asxshorts.errors import CacheError


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def cache_manager(temp_cache_dir):
    """Create a CacheManager instance for testing."""
    return CacheManager(temp_cache_dir)


def test_cache_dir_creation_failure():
    """Test cache directory creation failure."""
    # Use a path that will fail to create (e.g., under a read-only directory)
    with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
        with pytest.raises(CacheError, match="Failed to create cache directory"):
            manager = CacheManager("/invalid/path")
            # Trigger directory creation by attempting to write to cache
            manager.write_cached(date(2024, 1, 15), b"test data")


def test_cache_dir_creation_with_existing_dir(temp_cache_dir):
    """Test cache directory creation when directory already exists."""
    # Create the directory first
    cache_dir = Path(temp_cache_dir) / "existing"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Should not raise an error
    manager = CacheManager(str(cache_dir))
    assert manager.cache_dir == cache_dir.resolve()


def test_acquire_lock_timeout(cache_manager):
    """Test lock acquisition timeout."""
    test_date = date(2024, 1, 15)

    # Create a lock file manually to simulate existing lock
    lock_path = cache_manager._get_lock_path(test_date)
    lock_path.parent.mkdir(exist_ok=True)
    with open(lock_path, "w") as f:
        f.write("12345")

    # Should timeout and return False
    result = cache_manager._acquire_lock(test_date, timeout=0.1)
    assert result is False

    # Clean up
    lock_path.unlink()


def test_acquire_lock_success_after_wait(cache_manager):
    """Test lock acquisition success after brief wait."""
    test_date = date(2024, 1, 15)

    def delayed_lock_removal():
        """Remove lock after a short delay."""
        time.sleep(0.05)
        lock_path = cache_manager._get_lock_path(test_date)
        if lock_path.exists():
            lock_path.unlink()

    # Create a lock file that will be removed shortly
    lock_path = cache_manager._get_lock_path(test_date)
    lock_path.parent.mkdir(exist_ok=True)
    with open(lock_path, "w") as f:
        f.write("12345")

    # Start removal in background
    import threading

    thread = threading.Thread(target=delayed_lock_removal)
    thread.start()

    # Should eventually acquire lock
    result = cache_manager._acquire_lock(test_date, timeout=1.0)
    thread.join()
    assert result is True

    # Clean up
    cache_manager._release_lock(test_date)


def test_release_lock_failure(cache_manager):
    """Test lock release failure handling."""
    test_date = date(2024, 1, 15)

    # Mock unlink to raise OSError
    with patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")):
        # Should not raise exception, just log warning
        cache_manager._release_lock(test_date)


def test_read_cached_file_error(cache_manager):
    """Test read cached file with OS error."""
    test_date = date(2024, 1, 15)

    # Create a cache file
    cache_path = cache_manager._get_cache_path(test_date)
    cache_path.write_bytes(b"test data")

    # Mock pathlib.Path.open to raise OSError
    with patch("pathlib.Path.open", side_effect=OSError("Permission denied")):
        result = cache_manager.read_cached(test_date)
        assert result is None


def test_write_cached_lock_failure(cache_manager):
    """Test write cached with lock acquisition failure."""
    test_date = date(2024, 1, 15)

    with patch.object(cache_manager, "_acquire_lock", return_value=False):
        with pytest.raises(CacheError, match="Failed to acquire lock"):
            cache_manager.write_cached(test_date, b"test data")


def test_write_cached_os_error(cache_manager):
    """Test write cached with OS error during file operations."""
    test_date = date(2024, 1, 15)

    # Mock tempfile.NamedTemporaryFile to raise OSError
    with patch("tempfile.NamedTemporaryFile", side_effect=OSError("Disk full")):
        with pytest.raises(CacheError, match="Failed to write cache"):
            cache_manager.write_cached(test_date, b"test data")


def test_write_cached_rename_failure(cache_manager):
    """Test write cached with rename failure."""
    test_date = date(2024, 1, 15)

    # Mock os.rename to raise OSError
    with patch("os.rename", side_effect=OSError("Permission denied")):
        with pytest.raises(CacheError, match="Failed to write cache"):
            cache_manager.write_cached(test_date, b"test data")


def test_write_cached_temp_file_cleanup(cache_manager):
    """Test that temporary files are cleaned up on error."""
    test_date = date(2024, 1, 15)

    # Create a mock temporary file
    mock_tmp_file = Mock()
    mock_tmp_file.name = str(cache_manager.cache_dir / "test.tmp")
    mock_tmp_file.__enter__ = Mock(return_value=mock_tmp_file)
    mock_tmp_file.__exit__ = Mock(return_value=None)

    # Create the actual temp file
    Path(mock_tmp_file.name).touch()

    with patch("tempfile.NamedTemporaryFile", return_value=mock_tmp_file):
        with patch("os.rename", side_effect=OSError("Permission denied")):
            with patch("os.unlink") as mock_unlink:
                with pytest.raises(CacheError):
                    cache_manager.write_cached(test_date, b"test data")

                # Verify temp file cleanup was attempted
                mock_unlink.assert_called()


def test_clear_cache_os_error(cache_manager):
    """Test clear cache with OS error."""
    # Create a cache file
    test_date = date(2024, 1, 15)
    cache_path = cache_manager._get_cache_path(test_date)
    cache_path.write_bytes(b"test data")

    # Mock unlink to raise OSError
    with patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")):
        with pytest.raises(CacheError, match="Failed to clear cache"):
            cache_manager.clear_cache()


def test_cache_stats_os_error(cache_manager):
    """Test cache stats with OS error."""
    with patch("pathlib.Path.glob", side_effect=OSError("Permission denied")):
        with pytest.raises(CacheError, match="Failed to get cache stats"):
            cache_manager.cache_stats()


def test_cache_stats_with_invalid_files(cache_manager):
    """Test cache_stats when encountering invalid files."""
    # Create a cache file
    test_date = date(2024, 1, 15)
    cache_path = cache_manager._get_cache_path(test_date)
    cache_path.write_bytes(b"test data")

    # Mock stat to raise OSError for some files
    original_stat = Path.stat

    def mock_stat(self, *args, **kwargs):
        if self.name.endswith(".csv"):
            raise OSError("Permission denied")
        return original_stat(self, *args, **kwargs)

    with patch("pathlib.Path.stat", mock_stat):
        # Should raise CacheError when stat fails
        with pytest.raises(CacheError, match="Failed to get cache stats"):
            cache_manager.cache_stats()


def test_cleanup_stale_locks_os_error(cache_manager):
    """Test cleanup stale locks with OS error."""
    with patch("pathlib.Path.glob", side_effect=OSError("Permission denied")):
        # Should not raise exception, just log warning
        cache_manager.cleanup_stale_locks()


def test_cleanup_stale_locks_stat_error(cache_manager):
    """Test cleanup stale locks with stat error."""
    # Create a lock file
    test_date = date(2024, 1, 15)
    lock_path = cache_manager._get_lock_path(test_date)
    lock_path.parent.mkdir(exist_ok=True)
    lock_path.touch()

    # Mock stat to raise OSError
    with patch("pathlib.Path.stat", side_effect=OSError("Permission denied")):
        # Should not raise exception, just log warning
        cache_manager.cleanup_stale_locks()


def test_cleanup_stale_locks_unlink_error(cache_manager):
    """Test cleanup stale locks with unlink error."""
    # Create an old lock file
    test_date = date(2024, 1, 15)
    lock_path = cache_manager._get_lock_path(test_date)
    lock_path.parent.mkdir(exist_ok=True)
    lock_path.touch()

    # Make it appear old
    old_time = time.time() - 7200  # 2 hours ago
    os.utime(lock_path, (old_time, old_time))

    # Mock unlink to raise OSError
    with patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")):
        # Should not raise exception, just continue
        cache_manager.cleanup_stale_locks(max_age_seconds=3600)


def test_has_cached_empty_file(cache_manager):
    """Test has_cached with empty file."""
    test_date = date(2024, 1, 15)
    cache_path = cache_manager._get_cache_path(test_date)

    # Create empty file
    cache_path.touch()

    # Should return False for empty file
    assert cache_manager.has_cached(test_date) is False


def test_has_cached_nonexistent_file(cache_manager):
    """Test has_cached with nonexistent file."""
    test_date = date(2024, 1, 15)

    # Should return False for nonexistent file
    assert cache_manager.has_cached(test_date) is False


def test_expanduser_in_cache_dir():
    """Test that cache directory path is properly expanded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use ~ in path
        cache_dir = "~/test_cache"

        with patch("pathlib.Path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = Path(tmpdir) / "test_cache"
            manager = CacheManager(cache_dir)

            mock_expanduser.assert_called_once()
            assert str(manager.cache_dir).endswith("test_cache")


def test_lock_with_existing_pid(cache_manager):
    """Test lock behavior with existing PID in lock file."""
    test_date = date(2024, 1, 15)
    lock_path = cache_manager._get_lock_path(test_date)
    lock_path.parent.mkdir(exist_ok=True)

    # Create lock file with current PID
    with open(lock_path, "w") as f:
        f.write(str(os.getpid()))

    # Should timeout since lock exists
    result = cache_manager._acquire_lock(test_date, timeout=0.1)
    assert result is False

    # Clean up
    lock_path.unlink()


def test_cache_path_generation(cache_manager):
    """Test cache path generation for different dates."""
    test_date = date(2024, 1, 15)
    cache_path = cache_manager._get_cache_path(test_date)

    assert cache_path.name == "2024-01-15.csv"
    assert cache_path.parent == cache_manager.cache_dir


def test_lock_path_generation(cache_manager):
    """Test lock path generation for different dates."""
    test_date = date(2024, 1, 15)
    lock_path = cache_manager._get_lock_path(test_date)

    assert lock_path.name == "2024-01-15.csv.lock"
    assert lock_path.parent == cache_manager.locks_dir

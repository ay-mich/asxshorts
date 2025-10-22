"""Tests for CLI edge cases and error handling."""

import json
from datetime import date
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from asxshorts.cli import app
from asxshorts.errors import FetchError, NotFoundError
from asxshorts.models import FetchResult, RangeResult


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_fetch_result():
    """Create a sample FetchResult for testing."""
    return FetchResult(
        fetch_date=date(2024, 1, 15),
        record_count=2,
        from_cache=False,
        fetch_time_ms=100.0,
        url="https://example.com",
        records=[],
    )


@pytest.fixture
def sample_range_result():
    """Create a sample RangeResult for testing."""
    return RangeResult(
        start_date=date(2024, 1, 10),
        end_date=date(2024, 1, 12),
        total_records=2,
        total_fetch_time_ms=200.0,
        results={
            date(2024, 1, 10): FetchResult(
                fetch_date=date(2024, 1, 10),
                record_count=1,
                from_cache=False,
                fetch_time_ms=100.0,
                url="https://example.com",
                records=[],
            ),
            date(2024, 1, 12): FetchResult(
                fetch_date=date(2024, 1, 12),
                record_count=1,
                from_cache=False,
                fetch_time_ms=100.0,
                url="https://example.com",
                records=[],
            ),
        },
    )


def test_fetch_not_found_error(runner, sample_fetch_result):
    """Test fetch command with NotFoundError."""
    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_day.side_effect = NotFoundError(date(2024, 1, 15))

        result = runner.invoke(app, ["fetch", "2024-01-15"])

        assert result.exit_code == 1
        assert "No data found for 2024-01-15" in result.stderr


def test_fetch_general_error(runner):
    """Test fetch command with general FetchError."""
    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_day.side_effect = FetchError("Network error")

        result = runner.invoke(app, ["fetch", "2024-01-15"])

        assert result.exit_code == 1
        assert "Fetch failed: Network error" in result.stderr


def test_fetch_unexpected_error(runner):
    """Test fetch command with unexpected error."""
    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_day.side_effect = RuntimeError("Unexpected error")

        result = runner.invoke(app, ["fetch", "2024-01-15"])

        assert result.exit_code == 1
        assert "Unexpected error: Unexpected error" in result.stderr


def test_fetch_range_invalid_date_order(runner):
    """Test fetch_range with invalid date order."""
    result = runner.invoke(app, ["fetch-range", "2024-01-15", "2024-01-10"])

    assert result.exit_code == 1
    assert "Start date must be <= end date" in result.stderr


def test_fetch_range_with_failed_dates(runner, sample_range_result):
    """Test fetch_range with some failed dates."""
    # Modify the sample result to include failed dates
    sample_range_result.results = {
        date(2024, 1, 10): sample_range_result.results[date(2024, 1, 10)],
        date(2024, 1, 12): sample_range_result.results[date(2024, 1, 12)],
    }

    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_range.return_value = sample_range_result

        result = runner.invoke(app, ["fetch-range", "2024-01-10", "2024-01-12"])

        assert result.exit_code == 0
        assert "Found 2 total records" in result.stdout


def test_cache_info_command(runner):
    """Test cache_info command."""
    mock_stats = Mock()
    mock_stats.path = "/tmp/cache"
    mock_stats.count = 5
    mock_stats.size_bytes = 1024

    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.cache_stats.return_value = mock_stats

        result = runner.invoke(app, ["cache-info"])

        assert result.exit_code == 0
        assert "Cache Statistics:" in result.stdout
        assert "/tmp/cache" in result.stdout
        assert "5" in result.stdout


def test_clear_cache_with_confirmation(runner):
    """Test clear_cache with user confirmation."""
    mock_stats = Mock()
    mock_stats.count = 5
    mock_stats.size_bytes = 1024

    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.cache_stats.return_value = mock_stats

        # Test with confirmation (yes)
        result = runner.invoke(app, ["clear-cache"], input="y\n")

        assert result.exit_code == 0
        assert "Cache cleared" in result.stdout


def test_clear_cache_without_confirmation(runner):
    """Test clear_cache without user confirmation."""
    mock_stats = Mock()
    mock_stats.count = 5
    mock_stats.size_bytes = 1024

    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.cache_stats.return_value = mock_stats

        # Test without confirmation (no)
        result = runner.invoke(app, ["clear-cache"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout


def test_clear_cache_force(runner):
    """Test clear_cache with force flag."""
    mock_stats = Mock()
    mock_stats.count = 5
    mock_stats.size_bytes = 1024

    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.cache_stats.return_value = mock_stats

        result = runner.invoke(app, ["clear-cache", "--yes"])

        assert result.exit_code == 0
        assert "Cache cleared" in result.stdout


def test_clear_cache_empty(runner):
    """Test clear_cache when cache is already empty."""
    mock_stats = Mock()
    mock_stats.count = 0
    mock_stats.size_bytes = 0

    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.cache_stats.return_value = mock_stats

        result = runner.invoke(app, ["clear-cache"])

        assert result.exit_code == 0
        assert "Cache is already empty" in result.stdout


def test_cleanup_cache_command(runner):
    """Test cleanup_cache command."""
    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["cleanup-cache", "--max-age", "60"])

        assert result.exit_code == 0
        assert "Cleaned up cache files older than 60 days" in result.stdout
        mock_client.cleanup_cache.assert_called_once_with(60)


def test_version_command(runner):
    """Test version command."""
    with patch("asxshorts.cli.get_version", return_value="1.0.0"):
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "asxshorts 1.0.0" in result.stdout


def test_version_command_unknown(runner):
    """Test version command when version is unknown."""
    with patch("asxshorts.cli.get_version", side_effect=Exception("Not found")):
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "asxshorts unknown" in result.stdout


def test_custom_cache_dir_option(runner, sample_fetch_result):
    """Test custom cache directory option."""
    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        with patch("asxshorts.cli.ClientSettings") as mock_settings_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.fetch_day.return_value = sample_fetch_result

            result = runner.invoke(
                app, ["fetch", "2024-01-15", "--cache-dir", "/custom/cache"]
            )

            assert result.exit_code == 0
            mock_settings_class.assert_called_once_with(cache_dir="/custom/cache")


def test_fetch_with_output_file(runner, sample_fetch_result, tmp_path):
    """Test fetch command with output file."""
    output_file = tmp_path / "output.json"

    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_day.return_value = sample_fetch_result

        result = runner.invoke(
            app, ["fetch", "2024-01-15", "--output", str(output_file)]
        )

        assert result.exit_code == 0
        assert f"Saved to {output_file}" in result.stdout
        assert output_file.exists()

        # Verify JSON content
        with output_file.open() as f:
            data = json.load(f)
        assert data["date"] == "2024-01-15"
        assert data["record_count"] == 2


def test_fetch_range_with_output_file(runner, sample_range_result, tmp_path):
    """Test fetch_range command with output file."""
    output_file = tmp_path / "range_output.json"

    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_range.return_value = sample_range_result

        result = runner.invoke(
            app,
            ["fetch-range", "2024-01-10", "2024-01-12", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        assert f"Saved to {output_file}" in result.stdout
        assert output_file.exists()

        # Verify JSON content
        with output_file.open() as f:
            data = json.load(f)
        assert data["start_date"] == "2024-01-10"
        assert data["end_date"] == "2024-01-12"


def test_fetch_with_force_option(runner, sample_fetch_result):
    """Test fetch command with force option."""
    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_day.return_value = sample_fetch_result

        result = runner.invoke(app, ["fetch", "2024-01-15", "--force"])

        assert result.exit_code == 0
        mock_client.fetch_day.assert_called_once_with(date(2024, 1, 15), force=True)


def test_setup_logging_verbose(runner, sample_fetch_result):
    """Test verbose logging setup."""
    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        with patch("asxshorts.cli.setup_logging") as mock_setup_logging:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.fetch_day.return_value = sample_fetch_result

            result = runner.invoke(app, ["fetch", "2024-01-15", "--verbose"])

            assert result.exit_code == 0
            mock_setup_logging.assert_called_with(True)


def test_setup_logging_default(runner, sample_fetch_result):
    """Test default logging setup."""
    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        with patch("asxshorts.cli.setup_logging") as mock_setup_logging:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.fetch_day.return_value = sample_fetch_result

            result = runner.invoke(app, ["fetch", "2024-01-15"])

            assert result.exit_code == 0
            mock_setup_logging.assert_called_with(False)


def test_parse_date_invalid_format(runner):
    """Test fetch with invalid date format."""
    result = runner.invoke(app, ["fetch", "invalid-date"])

    assert result.exit_code == 1
    assert "Invalid date format" in result.stderr


def test_parse_date_today(runner, sample_fetch_result):
    """Test fetch with 'today' keyword."""
    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_day.return_value = sample_fetch_result

        result = runner.invoke(app, ["fetch", "today"])

        assert result.exit_code == 0


def test_parse_date_yesterday(runner, sample_fetch_result):
    """Test fetch with 'yesterday' keyword."""
    with patch("asxshorts.cli.ShortsClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_day.return_value = sample_fetch_result

        result = runner.invoke(app, ["fetch", "yesterday"])

        assert result.exit_code == 0


def test_main_function():
    """Test main function entry point."""
    with patch("asxshorts.cli.app") as mock_app:
        from asxshorts.cli import main

        main()
        mock_app.assert_called_once()

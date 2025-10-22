"""Tests for command-line interface functionality."""

import json
import tempfile
from datetime import date
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from asxshorts.cli import app, setup_logging
from asxshorts.errors import NotFoundError
from asxshorts.models import FetchResult, RangeResult, ShortRecord


class TestSetupLogging:
    """Test cases for setup_logging function."""

    @patch("asxshorts.cli.logging.basicConfig")
    def test_setup_logging_default(self, mock_basic_config):
        """Test setup_logging with default (non-verbose) settings."""
        setup_logging()
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == 20  # logging.INFO
        assert "%(asctime)s" in call_args[1]["format"]
        assert "%(name)s" in call_args[1]["format"]
        assert "%(levelname)s" in call_args[1]["format"]
        assert "%(message)s" in call_args[1]["format"]

    @patch("asxshorts.cli.logging.basicConfig")
    def test_setup_logging_verbose(self, mock_basic_config):
        """Test setup_logging with verbose settings."""
        setup_logging(verbose=True)

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == 10  # logging.DEBUG


class TestFetchCommand:
    """Test cases for fetch command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.test_date = date(2023, 12, 15)

        # Sample test data
        self.sample_record = ShortRecord(
            report_date=self.test_date,
            asx_code="CBA",
            company_name="COMMONWEALTH BANK OF AUSTRALIA",
            short_sold=1000000,
            issued_shares=100000000,
            percent_short=1.0,
            raw={"PRODUCT": "CBA", "SHORT QTY": "1000000"},
        )

        self.sample_fetch_result = FetchResult(
            fetch_date=self.test_date,
            record_count=1,
            from_cache=False,
            fetch_time_ms=100,
            url="https://example.com",
            records=[self.sample_record],
        )

    @patch("asxshorts.cli.ShortsClient")
    def test_fetch_success_with_date(self, mock_client_class):
        """Test successful fetch with specific date."""
        mock_client = Mock()
        mock_client.fetch_day.return_value = self.sample_fetch_result
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(app, ["fetch", "2023-12-15"])

        assert result.exit_code == 0
        assert "Fetching data for 2023-12-15" in result.stdout
        assert "Found 1 records" in result.stdout
        mock_client.fetch_day.assert_called_once_with(self.test_date, force=False)

    @patch("asxshorts.cli.ShortsClient")
    def test_fetch_today_default(self, mock_client_class):
        """Test fetch with 'today' keyword."""
        mock_client = Mock()
        mock_client.fetch_day.return_value = self.sample_fetch_result
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(app, ["fetch", "today"])

        assert result.exit_code == 0
        assert "Fetching data for" in result.stdout
        mock_client.fetch_day.assert_called_once()

    @patch("asxshorts.cli.ShortsClient")
    def test_fetch_not_found_error(self, mock_client_class):
        """Test fetch with NotFoundError."""
        mock_client = Mock()
        mock_client.fetch_day.side_effect = NotFoundError(date(2023, 12, 15))
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(app, ["fetch", "2023-12-15"])

        assert result.exit_code == 1
        # Error messages go to stderr, not stdout
        assert (
            "No data found for 2023-12-15" in result.stderr
            or "No data found for 2023-12-15" in result.stdout
        )

    @patch("asxshorts.cli.ShortsClient")
    def test_fetch_with_output_file(self, mock_client_class):
        """Test fetch with output file."""
        mock_client = Mock()
        mock_client.fetch_day.return_value = self.sample_fetch_result
        mock_client_class.return_value = mock_client

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_path = f.name

        result = self.runner.invoke(
            app, ["fetch", "2023-12-15", "--output", output_path]
        )

        assert result.exit_code == 0
        assert f"Saved to {output_path}" in result.stdout

        # Verify file contents
        with open(output_path) as f:
            data = json.load(f)
            assert data["date"] == "2023-12-15"
            assert data["record_count"] == 1

    @patch("asxshorts.cli.ShortsClient")
    def test_fetch_with_force_refresh(self, mock_client_class):
        """Test fetch with force refresh option."""
        mock_client = Mock()
        mock_client.fetch_day.return_value = self.sample_fetch_result
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(app, ["fetch", "2023-12-15", "--force"])

        assert result.exit_code == 0
        mock_client.fetch_day.assert_called_once_with(self.test_date, force=True)


class TestFetchRangeCommand:
    """Test cases for fetch-range command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.start_date = date(2023, 12, 1)
        self.end_date = date(2023, 12, 15)

        # Sample range result with correct field names
        self.sample_range_result = RangeResult(
            start_date=self.start_date,  # Correct field name
            end_date=self.end_date,  # Correct field name
            total_records=10,
            successful_dates=[self.start_date, self.end_date],
            failed_dates=[],
            total_fetch_time_ms=500,
            results={
                self.start_date: FetchResult(
                    fetch_date=self.start_date,
                    record_count=5,
                    from_cache=False,
                    fetch_time_ms=250,
                    url="https://example.com",
                    records=[],
                )
            },
        )

    @patch("asxshorts.cli.ShortsClient")
    def test_fetch_range_success(self, mock_client_class):
        """Test successful fetch range."""
        mock_client = Mock()
        mock_client.fetch_range.return_value = self.sample_range_result
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(app, ["fetch-range", "2023-12-01", "2023-12-15"])

        assert result.exit_code == 0
        assert "Fetching data from 2023-12-01 to 2023-12-15" in result.stdout

    def test_fetch_range_invalid_dates(self):
        """Test fetch range with invalid date order."""
        result = self.runner.invoke(app, ["fetch-range", "2023-12-15", "2023-12-01"])

        # Should handle invalid date range gracefully
        assert result.exit_code == 1
        assert (
            "Start date must be <= end date" in result.stderr
            or "Start date must be <= end date" in result.stdout
        )


class TestCacheCommands:
    """Test cases for cache management commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("asxshorts.cli.ShortsClient")
    def test_cache_info(self, mock_client_class):
        """Test cache info command."""
        mock_client = Mock()
        mock_stats = Mock()
        mock_stats.path = "/test/cache"
        mock_stats.count = 5
        mock_stats.size_bytes = 1024
        mock_client.cache_stats.return_value = mock_stats
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(app, ["cache-info"])

        assert result.exit_code == 0
        assert "5" in result.stdout
        assert "1,024" in result.stdout  # Note the comma formatting

    @patch("asxshorts.cli.ShortsClient")
    def test_clear_cache(self, mock_client_class):
        """Test clear cache command."""
        mock_client = Mock()
        mock_stats = Mock()
        mock_stats.count = 5
        mock_stats.size_bytes = 1024
        mock_client.cache_stats.return_value = mock_stats
        mock_client.clear_cache.return_value = None
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(app, ["clear-cache", "--yes"])

        assert result.exit_code == 0
        mock_client.clear_cache.assert_called_once()

    @patch("asxshorts.cli.ShortsClient")
    def test_cleanup_cache(self, mock_client_class):
        """Test cleanup cache command."""
        mock_client = Mock()
        mock_client.cleanup_cache.return_value = None
        mock_client_class.return_value = mock_client

        result = self.runner.invoke(app, ["cleanup-cache", "--max-age", "30"])

        assert result.exit_code == 0
        mock_client.cleanup_cache.assert_called_once()


class TestVersionCommand:
    """Test cases for version command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("asxshorts.cli.get_version")
    def test_version_command(self, mock_get_version):
        """Test version command success."""
        mock_get_version.return_value = "1.0.0"

        result = self.runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "1.0.0" in result.stdout

    @patch("asxshorts.cli.get_version")
    def test_version_command_package_not_found(self, mock_get_version):
        """Test version command when package not found."""
        from importlib.metadata import PackageNotFoundError

        mock_get_version.side_effect = PackageNotFoundError("asxshorts")

        result = self.runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "unknown" in result.stdout


class TestMainFunction:
    """Test cases for main function."""

    @patch("asxshorts.cli.app")
    def test_main_function(self, mock_app):
        """Test main function calls typer app."""
        from asxshorts.cli import main

        main()

        mock_app.assert_called_once()


class TestDateParsing:
    """Test cases for date parsing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_invalid_date_format(self):
        """Test invalid date format handling."""
        result = self.runner.invoke(app, ["fetch", "invalid-date"])

        assert result.exit_code == 1
        assert (
            "Invalid date format 'invalid-date'" in result.stderr
            or "Invalid date format 'invalid-date'" in result.stdout
        )

    @patch("asxshorts.cli.ShortsClient")
    def test_valid_date_formats(self, mock_client_class):
        """Test various valid date formats."""
        mock_client = Mock()
        mock_client.fetch_day.return_value = FetchResult(
            fetch_date=date.today(),
            record_count=0,
            from_cache=False,
            fetch_time_ms=100,
            url="https://example.com",
            records=[],
        )
        mock_client_class.return_value = mock_client

        # Test yesterday
        result = self.runner.invoke(app, ["fetch", "yesterday"])
        assert result.exit_code == 0

"""Tests for URL resolution functionality."""

from datetime import date
from unittest.mock import Mock, patch

import pytest
import requests

from asxshorts.errors import NotFoundError
from asxshorts.resolve import AsicResolver, ConfigurableResolver, DefaultResolver


class TestDefaultResolver:
    """Test cases for DefaultResolver."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session = Mock(spec=requests.Session)
        self.base_url = "https://www.asx.com.au"
        self.resolver = DefaultResolver(self.base_url, self.session)
        self.test_date = date(2023, 12, 15)

    def test_init(self):
        """Test resolver initialization."""
        resolver = DefaultResolver("https://example.com/", self.session)
        assert resolver.base_url == "https://example.com"
        assert resolver.session == self.session
        assert len(resolver.patterns) > 0
        assert "/data/short-selling/{date}.csv" in resolver.patterns

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base URL."""
        resolver = DefaultResolver("https://example.com/", self.session)
        assert resolver.base_url == "https://example.com"

    def test_url_for_pattern_match_success(self):
        """Test successful URL resolution via pattern matching."""
        # Mock successful HEAD request
        self.session.head.return_value.status_code = 200

        result = self.resolver.url_for(self.test_date)

        # Should return first successful pattern
        expected_url = f"{self.base_url}/data/short-selling/20231215.csv"
        assert result == expected_url

        # Verify HEAD request was made
        self.session.head.assert_called_once_with(expected_url, timeout=10)

    def test_url_for_pattern_match_with_dash_format(self):
        """Test URL resolution with dash-formatted date."""
        # First pattern fails, second succeeds
        self.session.head.side_effect = [
            Mock(status_code=404),  # First pattern fails
            Mock(status_code=200),  # Second pattern succeeds
        ]

        result = self.resolver.url_for(self.test_date)

        # Should try dash format for first pattern
        expected_url = f"{self.base_url}/data/short-selling/2023-12-15.csv"
        assert result == expected_url

        # Verify both HEAD requests were made
        assert self.session.head.call_count == 2

    def test_url_for_fallback_to_index(self):
        """Test fallback to HTML index parsing when patterns fail."""
        # All pattern attempts fail
        self.session.head.return_value.status_code = 404

        # Mock successful index parsing
        with patch.object(
            self.resolver,
            "_find_via_index",
            return_value="https://example.com/found.csv",
        ):
            result = self.resolver.url_for(self.test_date)
            assert result == "https://example.com/found.csv"

    def test_url_for_not_found(self):
        """Test NotFoundError when no URL is found."""
        # All pattern attempts fail
        self.session.head.return_value.status_code = 404

        # Index parsing also fails
        with patch.object(self.resolver, "_find_via_index", return_value=None):
            with pytest.raises(NotFoundError) as exc_info:
                self.resolver.url_for(self.test_date)

            assert exc_info.value.date_requested == self.test_date

    def test_url_exists_success(self):
        """Test _url_exists with successful response."""
        self.session.head.return_value.status_code = 200

        result = self.resolver._url_exists("https://example.com/test.csv")
        assert result is True

        self.session.head.assert_called_once_with(
            "https://example.com/test.csv", timeout=10
        )

    def test_url_exists_not_found(self):
        """Test _url_exists with 404 response."""
        self.session.head.return_value.status_code = 404

        result = self.resolver._url_exists("https://example.com/test.csv")
        assert result is False

    def test_url_exists_request_exception(self):
        """Test _url_exists with request exception."""
        self.session.head.side_effect = requests.RequestException("Connection error")

        result = self.resolver._url_exists("https://example.com/test.csv")
        assert result is False

    def test_find_via_index_success(self):
        """Test successful index parsing."""
        # Mock successful GET request with HTML content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<a href="20231215.csv">Short selling data</a>'
        self.session.get.return_value = mock_response

        with patch.object(
            self.resolver,
            "_parse_html_for_date",
            return_value="https://example.com/20231215.csv",
        ):
            result = self.resolver._find_via_index(self.test_date)
            assert result == "https://example.com/20231215.csv"

    def test_find_via_index_no_match(self):
        """Test index parsing with no matching files."""
        # Mock successful GET request but no matching content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<a href="other.csv">Other data</a>'
        self.session.get.return_value = mock_response

        with patch.object(self.resolver, "_parse_html_for_date", return_value=None):
            result = self.resolver._find_via_index(self.test_date)
            assert result is None

    def test_find_via_index_request_error(self):
        """Test index parsing with request error."""
        self.session.get.side_effect = requests.RequestException("Connection error")

        result = self.resolver._find_via_index(self.test_date)
        assert result is None

    def test_find_via_index_404_response(self):
        """Test index parsing with 404 response."""
        mock_response = Mock()
        mock_response.status_code = 404
        self.session.get.return_value = mock_response

        result = self.resolver._find_via_index(self.test_date)
        assert result is None

    def test_parse_html_for_date_direct_link(self):
        """Test HTML parsing with direct CSV link."""
        html = '<a href="20231215.csv">Download</a>'
        date_patterns = ["20231215", "2023-12-15"]
        base_url = "https://example.com/"

        result = self.resolver._parse_html_for_date(html, date_patterns, base_url)
        assert result == "https://example.com/20231215.csv"

    def test_parse_html_for_date_absolute_link(self):
        """Test HTML parsing with absolute CSV link."""
        html = '<a href="https://files.example.com/20231215.csv">Download</a>'
        date_patterns = ["20231215", "2023-12-15"]
        base_url = "https://example.com/"

        result = self.resolver._parse_html_for_date(html, date_patterns, base_url)
        assert result == "https://files.example.com/20231215.csv"

    def test_parse_html_for_date_text_pattern(self):
        """Test HTML parsing with date in link text."""
        html = '<a href="data.csv">Data for 20231215</a>'
        date_patterns = ["20231215", "2023-12-15"]
        base_url = "https://example.com/"

        result = self.resolver._parse_html_for_date(html, date_patterns, base_url)
        assert result == "https://example.com/data.csv"

    def test_parse_html_for_date_no_match(self):
        """Test HTML parsing with no matching patterns."""
        html = '<a href="other.csv">Other data</a>'
        date_patterns = ["20231215", "2023-12-15"]
        base_url = "https://example.com/"

        result = self.resolver._parse_html_for_date(html, date_patterns, base_url)
        assert result is None

    def test_parse_html_for_date_case_insensitive(self):
        """Test HTML parsing is case insensitive."""
        html = '<a href="20231215.CSV">Download</a>'
        date_patterns = ["20231215"]
        base_url = "https://example.com/"

        result = self.resolver._parse_html_for_date(html, date_patterns, base_url)
        assert result == "https://example.com/20231215.CSV"


class TestConfigurableResolver:
    """Test cases for ConfigurableResolver."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session = Mock(spec=requests.Session)
        self.base_url = "https://www.asx.com.au"
        self.test_date = date(2023, 12, 15)

    def test_init_default_patterns(self):
        """Test initialization with default patterns."""
        resolver = ConfigurableResolver(self.base_url, self.session)
        assert resolver.base_url == self.base_url
        assert resolver.session == self.session
        assert len(resolver.patterns) == 2
        assert "/data/short-selling/{date}.csv" in resolver.patterns
        assert "/short-selling/{date}.csv" in resolver.patterns


class TestAsicResolver:
    """Tests for ASIC JSON index resolver."""

    def setup_method(self):
        self.session = Mock(spec=requests.Session)
        self.base_url = "https://download.asic.gov.au"
        self.test_date = date(2023, 12, 15)

    def test_url_for_success(self):
        """Resolves URL from JSON index for a given date."""
        resolver = AsicResolver(self.base_url, self.session)

        # Mock JSON index
        mock_resp = Mock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = [
            {"date": "20231214", "version": "01"},
            {"date": "20231215", "version": "02"},
        ]
        self.session.get.return_value = mock_resp

        # Mock HEAD success for the constructed CSV URL
        head_resp = Mock(status_code=200)
        self.session.head.return_value = head_resp

        result = resolver.url_for(self.test_date)

        expected = f"{self.base_url}/short-selling/RR20231215-02-SSDailyAggShortPos.csv"
        assert result == expected

    def test_url_for_not_found(self):
        """Raises NotFoundError when date is not present in index."""
        resolver = AsicResolver(self.base_url, self.session)

        mock_resp = Mock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = [{"date": "20231214", "version": "01"}]
        self.session.get.return_value = mock_resp

        with pytest.raises(NotFoundError):
            resolver.url_for(self.test_date)

    def test_url_for_json_fetch_failure(self):
        """Raises NotFoundError when index fetch fails."""
        resolver = AsicResolver(self.base_url, self.session)
        self.session.get.side_effect = requests.RequestException("boom")

        with pytest.raises(NotFoundError):
            resolver.url_for(self.test_date)

    def test_init_custom_patterns(self):
        """Test initialization with custom patterns."""
        custom_patterns = ["/custom/{date}.csv", "/other/{date}.csv"]
        resolver = ConfigurableResolver(
            self.base_url, self.session, patterns=custom_patterns
        )
        assert resolver.patterns == custom_patterns

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base URL."""
        resolver = ConfigurableResolver("https://example.com/", self.session)
        assert resolver.base_url == "https://example.com"

    def test_url_for_success_first_pattern(self):
        """Test successful URL resolution with first pattern."""
        resolver = ConfigurableResolver(self.base_url, self.session)

        # Mock successful HEAD request
        self.session.head.return_value.status_code = 200

        result = resolver.url_for(self.test_date)

        # Should return first successful pattern with first date format
        expected_url = f"{self.base_url}/data/short-selling/20231215.csv"
        assert result == expected_url

        self.session.head.assert_called_once_with(expected_url, timeout=10)

    def test_url_for_success_second_date_format(self):
        """Test successful URL resolution with second date format."""
        resolver = ConfigurableResolver(self.base_url, self.session)

        # First date format fails, second succeeds
        self.session.head.side_effect = [
            Mock(status_code=404),  # First date format fails
            Mock(status_code=200),  # Second date format succeeds
        ]

        result = resolver.url_for(self.test_date)

        # Should return first pattern with second date format
        expected_url = f"{self.base_url}/data/short-selling/2023-12-15.csv"
        assert result == expected_url

        assert self.session.head.call_count == 2

    def test_url_for_success_third_date_format(self):
        """Test successful URL resolution with third date format."""
        resolver = ConfigurableResolver(self.base_url, self.session)

        # First two date formats fail, third succeeds
        self.session.head.side_effect = [
            Mock(status_code=404),  # 20231215 format fails
            Mock(status_code=404),  # 2023-12-15 format fails
            Mock(status_code=200),  # 15122023 format succeeds
        ]

        result = resolver.url_for(self.test_date)

        # Should return first pattern with third date format
        expected_url = f"{self.base_url}/data/short-selling/15122023.csv"
        assert result == expected_url

        assert self.session.head.call_count == 3

    def test_url_for_success_second_pattern(self):
        """Test successful URL resolution with second pattern."""
        resolver = ConfigurableResolver(self.base_url, self.session)

        # First pattern fails for all date formats, second pattern succeeds
        self.session.head.side_effect = [
            Mock(status_code=404),  # First pattern, first date format
            Mock(status_code=404),  # First pattern, second date format
            Mock(status_code=404),  # First pattern, third date format
            Mock(status_code=200),  # Second pattern, first date format
        ]

        result = resolver.url_for(self.test_date)

        # Should return second pattern with first date format
        expected_url = f"{self.base_url}/short-selling/20231215.csv"
        assert result == expected_url

        assert self.session.head.call_count == 4

    def test_url_for_request_exception(self):
        """Test URL resolution with request exception."""
        resolver = ConfigurableResolver(self.base_url, self.session)

        # All requests fail with exception
        self.session.head.side_effect = requests.RequestException("Connection error")

        with pytest.raises(NotFoundError) as exc_info:
            resolver.url_for(self.test_date)

        assert exc_info.value.date_requested == self.test_date

    def test_configurable_url_for_not_found(self):
        """Test NotFoundError for ConfigurableResolver when no pattern matches."""
        resolver = ConfigurableResolver(self.base_url, self.session)

        # All requests return 404
        self.session.head.return_value.status_code = 404

        with pytest.raises(NotFoundError) as exc_info:
            resolver.url_for(self.test_date)

        assert exc_info.value.date_requested == self.test_date

        # Should try all patterns with all date formats
        expected_calls = 2 * 3  # 2 patterns × 3 date formats
        assert self.session.head.call_count == expected_calls

    def test_url_for_custom_patterns(self):
        """Test URL resolution with custom patterns."""
        custom_patterns = ["/custom/{date}.csv"]
        resolver = ConfigurableResolver(
            self.base_url, self.session, patterns=custom_patterns
        )

        self.session.head.return_value.status_code = 200

        result = resolver.url_for(self.test_date)

        expected_url = f"{self.base_url}/custom/20231215.csv"
        assert result == expected_url

    def test_date_formats(self):
        """Test all supported date formats."""
        resolver = ConfigurableResolver(
            self.base_url, self.session, patterns=["/test/{date}.csv"]
        )

        # Test date: 2023-12-15
        test_date = date(2023, 12, 15)

        # Mock responses to capture all attempted URLs
        attempted_urls = []

        def mock_head(url, timeout=None):
            attempted_urls.append(url)
            return Mock(status_code=404)

        self.session.head.side_effect = mock_head

        with pytest.raises(NotFoundError):
            resolver.url_for(test_date)

        # Verify all expected date formats were tried
        expected_urls = [
            f"{self.base_url}/test/20231215.csv",  # YYYYMMDD
            f"{self.base_url}/test/2023-12-15.csv",  # YYYY-MM-DD
            f"{self.base_url}/test/15122023.csv",  # DDMMYYYY
        ]

        assert attempted_urls == expected_urls

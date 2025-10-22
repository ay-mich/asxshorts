"""URL resolution for ASX short selling data files.

Resolvers include:
- AsicResolver: discovers CSV URLs via the official ASIC JSON index
- DefaultResolver: pattern-based resolution + lightweight HTML index fallback
- ConfigurableResolver: simple pattern-only resolver
"""

import logging
import re
from datetime import date
from typing import Protocol
from urllib.parse import urljoin

import requests

from .errors import NotFoundError

logger = logging.getLogger(__name__)


class UrlResolver(Protocol):
    """Protocol for URL resolution strategies."""

    def url_for(self, d: date) -> str:
        """Resolve URL for given date."""
        ...


class AsicResolver:
    """Resolve URLs using ASIC JSON index feed.

    Expects `base_url` like "https://download.asic.gov.au" and fetches
    "/short-selling/short-selling-data.json" which maps dates to versions and
    file names. Builds the final CSV URL using the standard filename pattern.
    """

    INDEX_PATH = "/short-selling/short-selling-data.json"
    CSV_DIR = "/short-selling/"

    def __init__(self, base_url: str, session: requests.Session):
        """Create a resolver using the ASIC JSON feed.

        Args:
            base_url: Base URL such as "https://download.asic.gov.au".
            session: A configured ``requests.Session`` for HTTP calls.
        """
        self.base_url = base_url.rstrip("/")
        self.session = session
        # Simple in-memory cache of the index JSON for the lifetime of this resolver
        self._index_cache: list[dict] | None = None

    def url_for(self, d: date) -> str:
        """Resolve URL for given date via ASIC JSON index."""
        # Fetch and cache index JSON once per resolver instance
        if self._index_cache is None:
            try:
                resp = self.session.get(self.base_url + self.INDEX_PATH, timeout=20)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                # If index fetch fails for any reason, treat as not found
                raise NotFoundError(d) from e

            # Normalize entries list from various possible JSON shapes
            if isinstance(data, list):
                entries: list[dict] = data
            else:
                entries = data.get("data") or data.get("files") or []
                if not isinstance(entries, list):
                    entries = []
            self._index_cache = entries

        # The JSON structure contains entries with fields including date, version and/or filename/url.
        # We support flexible keys:
        #   - date keys: "date", "dataDate", "fileDate"
        #   - version keys: "version", "ver"
        #   - filename/url keys: "file", "filename", "fileName", "href", "url"
        target_keys = ("date", "dataDate", "fileDate")
        version_keys = ("version", "ver")
        file_keys = ("file", "filename", "fileName", "href", "url")
        date_str_yyyymmdd = d.strftime("%Y%m%d")
        date_str_dash = d.strftime("%Y-%m-%d")

        for entry in self._index_cache:
            try:
                # Normalize date
                found_date = None
                for dk in target_keys:
                    if dk in entry:
                        val = str(entry[dk])
                        # Strip non-digits for parsing, keep dash format too
                        if val.isdigit() and len(val) == 8:
                            found_date = f"{val[:4]}-{val[4:6]}-{val[6:8]}"
                        else:
                            found_date = val
                        break
                if not found_date:
                    continue

                if found_date not in (date_str_dash, date_str_yyyymmdd, date_str_dash):
                    # Format mismatch: also compare raw digits
                    raw_digits = found_date.replace("-", "")
                    if raw_digits != date_str_yyyymmdd:
                        continue

                # If filename/url is provided directly, prefer it
                direct_url = None
                for fk in file_keys:
                    if fk in entry:
                        direct_url = str(entry[fk])
                        break

                if direct_url:
                    if direct_url.startswith("http"):
                        url = direct_url
                    else:
                        url = urljoin(self.base_url + "/short-selling/", direct_url)
                else:
                    # Otherwise construct using version if available
                    version = None
                    for vk in version_keys:
                        if vk in entry:
                            version = str(entry[vk]).zfill(2)
                            break
                    if version is None:
                        continue
                    fname = f"RR{date_str_yyyymmdd}-{version}-SSDailyAggShortPos.csv"
                    url = self.base_url + self.CSV_DIR + fname

                # HEAD check (optional)
                try:
                    r = self.session.head(url, timeout=10)
                    if r.status_code == 200:
                        return url
                except requests.RequestException:
                    # Fall through to try other entries
                    pass
            except (KeyError, ValueError, TypeError, AttributeError):
                # KeyError: missing expected keys in entry dict
                # ValueError: invalid data conversion (e.g., str to int)
                # TypeError: unexpected data types
                # AttributeError: missing methods/attributes on objects
                continue

        raise NotFoundError(d)


class DefaultResolver:
    """Default URL resolver with pattern matching and HTML fallback."""

    def __init__(self, base_url: str, session: requests.Session):
        """Initialize the DefaultResolver.

        Args:
            base_url: Base URL for the ASX website.
            session: HTTP session for making requests.
        """
        self.base_url = base_url.rstrip("/")
        self.session = session

        # Common ASX file patterns
        self.patterns = [
            "/data/short-selling/{date}.csv",
            "/data/short-selling/short-selling-{date}.csv",
            "/data/short-selling/{date}-short-selling.csv",
            "/asxdata/short-selling/{date}.csv",
            "/short-selling/{date}.csv",
        ]

    def url_for(self, d: date) -> str:
        """Resolve URL for given date using patterns and fallback."""
        date_str = d.strftime("%Y%m%d")
        date_dash = d.strftime("%Y-%m-%d")

        # Try common patterns first
        for pattern in self.patterns:
            for date_format in [date_str, date_dash]:
                url = self.base_url + pattern.format(date=date_format)
                if self._url_exists(url):
                    logger.debug(f"Found URL via pattern: {url}")
                    return url

        # Fallback to HTML index parsing
        index_url = self._find_via_index(d)
        if index_url:
            logger.debug(f"Found URL via index: {index_url}")
            return index_url

        raise NotFoundError(d)

    def _url_exists(self, url: str) -> bool:
        """Check if URL exists with HEAD request."""
        try:
            response = self.session.head(url, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _find_via_index(self, d: date) -> str | None:
        """Find URL by parsing HTML index pages."""
        date_str = d.strftime("%Y%m%d")
        date_dash = d.strftime("%Y-%m-%d")
        date_patterns = [date_str, date_dash, d.strftime("%d%m%Y")]

        # Common index page locations
        index_urls = [
            f"{self.base_url}/data/short-selling/",
            f"{self.base_url}/asxdata/short-selling/",
            f"{self.base_url}/short-selling/",
            f"{self.base_url}/data/",
        ]

        for index_url in index_urls:
            try:
                response = self.session.get(index_url, timeout=15)
                if response.status_code != 200:
                    continue

                html_content = response.text
                found_url = self._parse_html_for_date(
                    html_content, date_patterns, index_url
                )
                if found_url:
                    return found_url

            except requests.RequestException as e:
                logger.debug(f"Failed to fetch index {index_url}: {e}")
                continue

        return None

    def _parse_html_for_date(
        self, html: str, date_patterns: list[str], base_url: str
    ) -> str | None:
        """Parse HTML content to find CSV links for target date."""
        # Look for CSV links containing any of our date patterns
        csv_link_pattern = r'href=["\']([^"\']*\.csv[^"\']*)["\']'
        csv_links = re.findall(csv_link_pattern, html, re.IGNORECASE)

        for link in csv_links:
            for date_pattern in date_patterns:
                if date_pattern in link:
                    # Convert relative URLs to absolute
                    if link.startswith("http"):
                        return str(link)
                    else:
                        return str(urljoin(base_url, link))

        # Also try looking for date patterns in link text
        for date_pattern in date_patterns:
            # Pattern to find links with date in the text
            text_pattern = rf'<a[^>]*href=["\']([^"\']*)["\'][^>]*>[^<]*{re.escape(date_pattern)}[^<]*</a>'
            matches = re.findall(text_pattern, html, re.IGNORECASE)
            for match in matches:
                if match.endswith(".csv") or "csv" in match.lower():
                    return str(urljoin(base_url, match))

        return None


class CompositeResolver:
    """Try ASIC index resolution first, then default heuristics."""

    def __init__(self, base_url: str, session: requests.Session):
        """Initialize a composite resolver that tries ASIC first then defaults.

        Args:
            base_url: Base URL for the target website.
            session: HTTP session used by both underlying resolvers.
        """
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.asic = AsicResolver(self.base_url, self.session)
        self.default = DefaultResolver(self.base_url, self.session)

    def url_for(self, d: date) -> str:
        """Resolve URL by trying ASIC index first, then default heuristics."""
        try:
            return self.asic.url_for(d)
        except NotFoundError:
            return self.default.url_for(d)

    def _parse_html_for_date(
        self, html: str, date_patterns: list[str], base_url: str
    ) -> str | None:
        """Parse HTML content to find CSV links for target date."""
        # Look for CSV links containing any of our date patterns
        csv_link_pattern = r'href=["\']([^"\']*\.csv[^"\']*)["\']'
        csv_links = re.findall(csv_link_pattern, html, re.IGNORECASE)

        for link in csv_links:
            for date_pattern in date_patterns:
                if date_pattern in link:
                    # Convert relative URLs to absolute
                    if link.startswith("http"):
                        return str(link)
                    else:
                        return str(urljoin(base_url, link))

        # Also try looking for date patterns in link text
        for date_pattern in date_patterns:
            # Pattern to find links with date in the text
            text_pattern = rf'<a[^>]*href=["\']([^"\']*)["\'][^>]*>[^<]*{re.escape(date_pattern)}[^<]*</a>'
            matches = re.findall(text_pattern, html, re.IGNORECASE)
            for match in matches:
                if match.endswith(".csv") or "csv" in match.lower():
                    return str(urljoin(base_url, match))

        return None


class ConfigurableResolver:
    """Configurable resolver that allows custom patterns and base URLs."""

    def __init__(
        self,
        base_url: str,
        session: requests.Session,
        patterns: list[str] | None = None,
    ):
        """Initialize the ConfigurableResolver.

        Args:
            base_url: Base URL for the ASX website.
            session: HTTP session for making requests.
            patterns: Custom URL patterns to try. If None, uses default patterns.
        """
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.patterns = patterns or [
            "/data/short-selling/{date}.csv",
            "/short-selling/{date}.csv",
        ]

    def url_for(self, d: date) -> str:
        """Resolve URL using configured patterns."""
        date_formats = [
            d.strftime("%Y%m%d"),
            d.strftime("%Y-%m-%d"),
            d.strftime("%d%m%Y"),
        ]

        for pattern in self.patterns:
            for date_format in date_formats:
                url = self.base_url + pattern.format(date=date_format)
                try:
                    response = self.session.head(url, timeout=10)
                    if response.status_code == 200:
                        return url
                except requests.RequestException:
                    continue

        raise NotFoundError(d)

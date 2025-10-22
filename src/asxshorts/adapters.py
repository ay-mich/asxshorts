"""Optional adapters for pandas and polars integration.

This module provides lightweight helpers to convert records returned by
``ShortsClient`` into pandas or polars DataFrames without imposing hard
dependencies. Use the convenience functions ``to_pandas`` and ``to_polars``
if you already have your data, or the adapter classes to fetch and convert
in one step.
"""

from datetime import date
from typing import Any

from .client import ShortsClient

# Optional imports at module level (to satisfy linters while avoiding hard deps)
try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - environment without pandas
    pd = None  # type: ignore[assignment]

try:
    import polars as pl  # type: ignore
except Exception:  # pragma: no cover - environment without polars
    pl = None  # type: ignore[assignment]


class PandasAdapter:
    """Adapter for pandas DataFrame integration."""

    def __init__(self, client: ShortsClient):
        """Initialize with a ShortsClient instance."""
        self.client = client
        if pd is None:
            raise ImportError(
                "pandas is required for PandasAdapter. "
                "Install with: pip install 'asxshorts[pandas]'"
            )
        self.pd = pd  # type: ignore[assignment]

    def fetch_day_df(self, d: date, *, force: bool = False) -> "pd.DataFrame":
        """Fetch data for a single date as pandas DataFrame.

        Args:
            d: Target date
            force: Bypass cache if True

        Returns:
            pandas DataFrame with short selling data
        """
        result = self.client.fetch_day(d, force=force)
        records_dict = [record.model_dump() for record in result.records]
        return self._records_to_dataframe(records_dict)

    def fetch_range_df(
        self, start: date, end: date, *, force: bool = False
    ) -> "pd.DataFrame":
        """Fetch data for a date range as pandas DataFrame.

        Args:
            start: Start date (inclusive)
            end: End date (inclusive)
            force: Bypass cache if True

        Returns:
            pandas DataFrame with short selling data
        """
        result = self.client.fetch_range(start, end, force=force)
        all_records = []
        for fetch_result in result.results.values():
            all_records.extend([record.model_dump() for record in fetch_result.records])
        return self._records_to_dataframe(all_records)

    def _records_to_dataframe(self, records: list[dict[str, Any]]) -> "pd.DataFrame":
        """Convert records to pandas DataFrame with proper types.

        Supports both normalized keys from this package
        (report_date, asx_code, company_name, short_sold, issued_shares, percent_short)
        and legacy/example keys (date, product, short_qty, total_qty, short_pct).
        """
        if not records:
            # Return empty DataFrame with expected columns
            return self.pd.DataFrame(
                columns=["date", "product", "short_qty", "total_qty", "short_pct"]
            )

        df = self.pd.DataFrame(records)

        # Ensure proper data types
        if "date" in df.columns:
            df["date"] = self.pd.to_datetime(df["date"], errors="coerce")
        if "report_date" in df.columns:
            df["report_date"] = self.pd.to_datetime(df["report_date"], errors="coerce")

        # Convert numeric columns
        for col in (
            "short_qty",
            "total_qty",
            "short_pct",
            "short_sold",
            "issued_shares",
            "percent_short",
        ):
            if col in df.columns:
                df[col] = self.pd.to_numeric(df[col], errors="coerce")

        return df


class PolarsAdapter:
    """Adapter for polars DataFrame integration."""

    def __init__(self, client: ShortsClient):
        """Initialize with a ShortsClient instance."""
        self.client = client
        if pl is None:
            raise ImportError(
                "polars is required for PolarsAdapter. "
                "Install with: pip install 'asxshorts[polars]'"
            )
        self.pl = pl  # type: ignore[assignment]

    def fetch_day_df(self, d: date, *, force: bool = False) -> "pl.DataFrame":
        """Fetch data for a single date as polars DataFrame.

        Args:
            d: Target date
            force: Bypass cache if True

        Returns:
            polars DataFrame with short selling data
        """
        result = self.client.fetch_day(d, force=force)
        records_dict = [record.model_dump() for record in result.records]
        return self._records_to_dataframe(records_dict)

    def fetch_range_df(
        self, start: date, end: date, *, force: bool = False
    ) -> "pl.DataFrame":
        """Fetch data for a date range as polars DataFrame.

        Args:
            start: Start date (inclusive)
            end: End date (inclusive)
            force: Bypass cache if True

        Returns:
            polars DataFrame with short selling data
        """
        result = self.client.fetch_range(start, end, force=force)
        all_records = []
        for fetch_result in result.results.values():
            all_records.extend([record.model_dump() for record in fetch_result.records])
        return self._records_to_dataframe(all_records)

    def _records_to_dataframe(self, records: list[dict[str, Any]]) -> "pl.DataFrame":
        """Convert records to polars DataFrame with proper types.

        Supports both normalized keys and legacy/example keys.
        """
        if not records:
            # Return empty DataFrame with expected schema
            return self.pl.DataFrame(
                schema={
                    "date": self.pl.Date,
                    "product": self.pl.Utf8,
                    "short_qty": self.pl.Int64,
                    "total_qty": self.pl.Int64,
                    "short_pct": self.pl.Float64,
                }
            )

        df = self.pl.DataFrame(records)

        # Cast to proper types
        df = df.with_columns(
            [
                self.pl.col("date").str.to_date() if "date" in df.columns else None,
                self.pl.col("report_date").str.to_date()
                if "report_date" in df.columns
                else None,
                self.pl.col("short_qty").cast(self.pl.Int64, strict=False)
                if "short_qty" in df.columns
                else None,
                self.pl.col("total_qty").cast(self.pl.Int64, strict=False)
                if "total_qty" in df.columns
                else None,
                self.pl.col("short_pct").cast(self.pl.Float64, strict=False)
                if "short_pct" in df.columns
                else None,
                self.pl.col("short_sold").cast(self.pl.Int64, strict=False)
                if "short_sold" in df.columns
                else None,
                self.pl.col("issued_shares").cast(self.pl.Int64, strict=False)
                if "issued_shares" in df.columns
                else None,
                self.pl.col("percent_short").cast(self.pl.Float64, strict=False)
                if "percent_short" in df.columns
                else None,
            ]
        )

        return df


def to_pandas(
    data: list[dict[str, Any]] | list[Any],
) -> "pd.DataFrame":
    """Convert a list of records to a pandas DataFrame.

    Accepts a list of ShortRecord models or dicts (e.g., via model_dump()).
    Requires pandas to be installed. This helper has no network or client side-effects.
    """
    if pd is None:
        raise ImportError(
            "pandas is required for to_pandas. Install with: pip install 'asxshorts[pandas]'"
        )

    # Normalize input items into dicts
    normalized: list[dict[str, Any]] = []
    for item in data:
        if hasattr(item, "model_dump"):
            normalized.append(item.model_dump())
        else:
            normalized.append(item)  # type: ignore[arg-type]

    # Create DataFrame and coerce types similarly to PandasAdapter
    if not normalized:
        return pd.DataFrame(
            columns=["date", "product", "short_qty", "total_qty", "short_pct"]
        )  # type: ignore[return-value]

    df = pd.DataFrame(normalized)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "report_date" in df.columns:
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    for col in (
        "short_qty",
        "total_qty",
        "short_pct",
        "short_sold",
        "issued_shares",
        "percent_short",
    ):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df  # type: ignore[return-value]


def to_polars(data: list[dict[str, Any]] | list[Any]) -> "pl.DataFrame":
    """Convert a list of records to a polars DataFrame.

    Accepts a list of ShortRecord models or dicts (e.g., via model_dump()).
    Requires polars to be installed. This helper has no network or client side-effects.
    """
    if pl is None:
        raise ImportError(
            "polars is required for to_polars. Install with: pip install 'asxshorts[polars]'"
        )

    # Normalize input items into dicts
    normalized: list[dict[str, Any]] = []
    for item in data:
        if hasattr(item, "model_dump"):
            normalized.append(item.model_dump())
        else:
            normalized.append(item)  # type: ignore[arg-type]

    # Create DataFrame and coerce types similarly to PolarsAdapter
    if not normalized:
        return pl.DataFrame(
            schema={
                "date": pl.Date,
                "product": pl.Utf8,
                "short_qty": pl.Int64,
                "total_qty": pl.Int64,
                "short_pct": pl.Float64,
            }
        )

    df = pl.DataFrame(normalized)
    df = df.with_columns(
        [
            (pl.col("date").str.to_date() if "date" in df.columns else None),
            (
                pl.col("report_date").str.to_date()
                if "report_date" in df.columns
                else None
            ),
            (
                pl.col("short_qty").cast(pl.Int64, strict=False)
                if "short_qty" in df.columns
                else None
            ),
            (
                pl.col("total_qty").cast(pl.Int64, strict=False)
                if "total_qty" in df.columns
                else None
            ),
            (
                pl.col("short_pct").cast(pl.Float64, strict=False)
                if "short_pct" in df.columns
                else None
            ),
            (
                pl.col("short_sold").cast(pl.Int64, strict=False)
                if "short_sold" in df.columns
                else None
            ),
            (
                pl.col("issued_shares").cast(pl.Int64, strict=False)
                if "issued_shares" in df.columns
                else None
            ),
            (
                pl.col("percent_short").cast(pl.Float64, strict=False)
                if "percent_short" in df.columns
                else None
            ),
        ]
    )
    return df


def create_pandas_adapter(client: ShortsClient | None = None) -> PandasAdapter:
    """Create a PandasAdapter with optional client.

    Args:
        client: ShortsClient instance, creates default if None

    Returns:
        PandasAdapter instance
    """
    if client is None:
        client = ShortsClient()
    return PandasAdapter(client)


def create_polars_adapter(client: ShortsClient | None = None) -> PolarsAdapter:
    """Create a PolarsAdapter with optional client.

    Args:
        client: ShortsClient instance, creates default if None

    Returns:
        PolarsAdapter instance
    """
    if client is None:
        client = ShortsClient()
    return PolarsAdapter(client)

"""Tests for pandas and polars adapter functionality."""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from asxshorts.adapters import (
    PandasAdapter,
    PolarsAdapter,
    create_pandas_adapter,
    create_polars_adapter,
)
from asxshorts.client import ShortsClient
from asxshorts.models import FetchResult, RangeResult, ShortRecord


class TestPandasAdapter:
    """Test cases for PandasAdapter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=ShortsClient)
        self.test_date = date(2023, 12, 15)

        # Sample test data with all required fields
        self.sample_records = [
            ShortRecord(
                report_date=self.test_date,
                asx_code="ABC",
                company_name="ABC Company",
                short_sold=1000,
                issued_shares=10000,
                percent_short=10.0,
                raw={"PRODUCT": "ABC", "SHORT QTY": "1000"},  # Add required raw field
            ),
            ShortRecord(
                report_date=self.test_date,
                asx_code="XYZ",
                company_name="XYZ Company",
                short_sold=2000,
                issued_shares=20000,
                percent_short=10.0,
                raw={"PRODUCT": "XYZ", "SHORT QTY": "2000"},  # Add required raw field
            ),
        ]

        self.sample_fetch_result = FetchResult(
            fetch_date=self.test_date,
            record_count=2,
            from_cache=False,
            fetch_time_ms=100.0,
            url="https://example.com/data.csv",
            records=self.sample_records,
        )

    def test_init_without_pandas(self):
        """Test PandasAdapter initialization without pandas installed."""
        with patch("asxshorts.adapters.pd", None):
            with pytest.raises(ImportError, match="pandas is required"):
                PandasAdapter(self.mock_client)

    def test_init_with_pandas(self):
        """Test PandasAdapter initialization with pandas available."""
        mock_pd = Mock()
        with patch("asxshorts.adapters.pd", mock_pd):
            adapter = PandasAdapter(self.mock_client)
            assert adapter.client == self.mock_client
            assert adapter.pd == mock_pd

    def test_fetch_day_df_success(self):
        """Test successful fetch_day_df operation."""
        # Setup mocks
        mock_pd = Mock()
        mock_df = Mock()

        # Mock DataFrame columns properly
        mock_df.columns = [
            "asx_code",
            "company_name",
            "short_sold",
            "issued_shares",
            "percent_short",
            "report_date",
        ]
        mock_df.__contains__ = Mock(return_value=False)  # No "date" column in this case
        mock_df.__getitem__ = Mock(return_value=Mock())
        mock_df.__setitem__ = Mock()

        mock_pd.DataFrame.return_value = mock_df
        mock_pd.to_datetime = Mock()
        mock_pd.to_numeric = Mock()
        self.mock_client.fetch_day.return_value = self.sample_fetch_result

        with patch("asxshorts.adapters.pd", mock_pd):
            adapter = PandasAdapter(self.mock_client)
            result = adapter.fetch_day_df(self.test_date)

            # Verify client was called correctly
            self.mock_client.fetch_day.assert_called_once_with(
                self.test_date, force=False
            )

            # Verify DataFrame creation
            mock_pd.DataFrame.assert_called_once()
            assert result == mock_df

    def test_fetch_day_df_with_force(self):
        """Test fetch_day_df with force parameter."""
        mock_pd = Mock()
        mock_df = Mock()

        # Mock DataFrame columns properly
        mock_df.columns = [
            "asx_code",
            "company_name",
            "short_sold",
            "issued_shares",
            "percent_short",
            "report_date",
        ]
        mock_df.__contains__ = Mock(return_value=False)
        mock_df.__getitem__ = Mock(return_value=Mock())
        mock_df.__setitem__ = Mock()

        mock_pd.DataFrame.return_value = mock_df
        mock_pd.to_datetime = Mock()
        mock_pd.to_numeric = Mock()
        self.mock_client.fetch_day.return_value = self.sample_fetch_result

        with patch("asxshorts.adapters.pd", mock_pd):
            adapter = PandasAdapter(self.mock_client)
            result = adapter.fetch_day_df(self.test_date, force=True)

            self.mock_client.fetch_day.assert_called_once_with(
                self.test_date, force=True
            )
            assert result == mock_df

    def test_fetch_range_df_success(self):
        """Test successful fetch_range_df operation."""
        # Setup range result with correct field names
        range_result = RangeResult(
            start_date=date(2023, 12, 1),  # Correct field name
            end_date=date(2023, 12, 15),  # Correct field name
            total_records=2,
            successful_dates=[self.test_date],
            failed_dates=[],
            total_fetch_time_ms=200.0,
            results={self.test_date: self.sample_fetch_result},
        )

        mock_pd = Mock()
        mock_df = Mock()

        # Mock DataFrame columns properly
        mock_df.columns = [
            "asx_code",
            "company_name",
            "short_sold",
            "issued_shares",
            "percent_short",
            "report_date",
        ]
        mock_df.__contains__ = Mock(return_value=False)
        mock_df.__getitem__ = Mock(return_value=Mock())
        mock_df.__setitem__ = Mock()

        mock_pd.DataFrame.return_value = mock_df
        mock_pd.to_datetime = Mock()
        mock_pd.to_numeric = Mock()
        self.mock_client.fetch_range.return_value = range_result

        with patch("asxshorts.adapters.pd", mock_pd):
            adapter = PandasAdapter(self.mock_client)
            result = adapter.fetch_range_df(date(2023, 12, 1), date(2023, 12, 15))

            # Verify client was called correctly
            self.mock_client.fetch_range.assert_called_once_with(
                date(2023, 12, 1), date(2023, 12, 15), force=False
            )

            # Verify DataFrame creation
            mock_pd.DataFrame.assert_called_once()
            assert result == mock_df

    def test_fetch_range_df_with_force(self):
        """Test fetch_range_df with force parameter."""
        range_result = RangeResult(
            start_date=date(2023, 12, 1),
            end_date=date(2023, 12, 15),
            total_records=2,
            successful_dates=[self.test_date],
            failed_dates=[],
            total_fetch_time_ms=200.0,
            results={self.test_date: self.sample_fetch_result},
        )

        mock_pd = Mock()
        mock_df = Mock()

        # Mock DataFrame columns properly
        mock_df.columns = [
            "asx_code",
            "company_name",
            "short_sold",
            "issued_shares",
            "percent_short",
            "report_date",
        ]
        mock_df.__contains__ = Mock(return_value=False)
        mock_df.__getitem__ = Mock(return_value=Mock())
        mock_df.__setitem__ = Mock()

        mock_pd.DataFrame.return_value = mock_df
        mock_pd.to_datetime = Mock()
        mock_pd.to_numeric = Mock()
        self.mock_client.fetch_range.return_value = range_result

        with patch("asxshorts.adapters.pd", mock_pd):
            adapter = PandasAdapter(self.mock_client)
            result = adapter.fetch_range_df(
                date(2023, 12, 1), date(2023, 12, 15), force=True
            )

            self.mock_client.fetch_range.assert_called_once_with(
                date(2023, 12, 1), date(2023, 12, 15), force=True
            )
            assert result == mock_df

    def test_records_to_dataframe_empty(self):
        """Test _records_to_dataframe with empty records."""
        mock_pd = Mock()
        mock_df = Mock()
        mock_pd.DataFrame.return_value = mock_df

        with patch("asxshorts.adapters.pd", mock_pd):
            adapter = PandasAdapter(self.mock_client)
            result = adapter._records_to_dataframe([])

            # Should create DataFrame with expected columns for empty case
            mock_pd.DataFrame.assert_called_once_with(
                columns=["date", "product", "short_qty", "total_qty", "short_pct"]
            )
            assert result == mock_df

    def test_records_to_dataframe_with_data(self):
        """Test _records_to_dataframe with actual records."""
        mock_pd = Mock()
        mock_df = Mock()

        # Mock DataFrame columns properly - simulate having "date" column
        mock_df.columns = ["date", "product", "short_qty", "total_qty", "short_pct"]
        mock_df.__contains__ = Mock(
            side_effect=lambda x: x in ["date", "short_qty", "total_qty", "short_pct"]
        )
        mock_df.__getitem__ = Mock(return_value=Mock())
        mock_df.__setitem__ = Mock()

        mock_pd.DataFrame.return_value = mock_df
        mock_pd.to_datetime = Mock()
        mock_pd.to_numeric = Mock()

        with patch("asxshorts.adapters.pd", mock_pd):
            adapter = PandasAdapter(self.mock_client)
            records_dict = [record.model_dump() for record in self.sample_records]
            result = adapter._records_to_dataframe(records_dict)

            # Verify DataFrame creation with record data
            mock_pd.DataFrame.assert_called_once_with(records_dict)
            assert result == mock_df


class TestPolarsAdapter:
    """Test cases for PolarsAdapter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=ShortsClient)
        self.test_date = date(2023, 12, 15)

        # Sample test data with all required fields
        self.sample_records = [
            ShortRecord(
                report_date=self.test_date,
                asx_code="ABC",
                company_name="ABC Company",
                short_sold=1000,
                issued_shares=10000,
                percent_short=10.0,
                raw={"PRODUCT": "ABC", "SHORT QTY": "1000"},
            ),
            ShortRecord(
                report_date=self.test_date,
                asx_code="XYZ",
                company_name="XYZ Company",
                short_sold=2000,
                issued_shares=20000,
                percent_short=10.0,
                raw={"PRODUCT": "XYZ", "SHORT QTY": "2000"},
            ),
        ]

        self.sample_fetch_result = FetchResult(
            fetch_date=self.test_date,
            record_count=2,
            from_cache=False,
            fetch_time_ms=100.0,
            url="https://example.com/data.csv",
            records=self.sample_records,
        )

    def test_init_without_polars(self):
        """Test PolarsAdapter initialization without polars installed."""
        with patch("asxshorts.adapters.pl", None):
            with pytest.raises(ImportError, match="polars is required"):
                PolarsAdapter(self.mock_client)

    def test_init_with_polars(self):
        """Test PolarsAdapter initialization with polars available."""
        mock_pl = Mock()

        with patch("asxshorts.adapters.pl", mock_pl):
            adapter = PolarsAdapter(self.mock_client)
            assert adapter.client == self.mock_client
            assert adapter.pl == mock_pl

    def test_fetch_day_df_success(self):
        """Test successful fetch_day_df operation."""
        # Setup mocks
        mock_pl = Mock()
        mock_df = Mock()
        mock_df_with_columns = Mock()

        # Mock DataFrame columns properly
        mock_df.columns = [
            "asx_code",
            "company_name",
            "short_sold",
            "issued_shares",
            "percent_short",
            "report_date",
        ]
        mock_df.__contains__ = Mock(
            return_value=False
        )  # No expected columns in this case

        mock_pl.DataFrame.return_value = mock_df
        mock_df.with_columns.return_value = mock_df_with_columns

        # Mock polars column operations
        expr = Mock()
        expr.str.to_date.return_value = "date_col"
        expr_after_cast = Mock()
        expr.cast.return_value = expr_after_cast
        expr_after_cast.dt.date.return_value = "report_date_col"
        mock_pl.col.return_value = expr
        mock_pl.Datetime = Mock(return_value="ms_dt")
        mock_pl.Int64 = "Int64"
        mock_pl.Float64 = "Float64"
        # Ensure df.schema supports subscription
        mock_pl.Date = "Date"
        mock_df.schema = {"report_date": "Utf8"}

        self.mock_client.fetch_day.return_value = self.sample_fetch_result

        with patch("asxshorts.adapters.pl", mock_pl):
            adapter = PolarsAdapter(self.mock_client)
            result = adapter.fetch_day_df(self.test_date)

            # Verify client was called correctly
            self.mock_client.fetch_day.assert_called_once_with(
                self.test_date, force=False
            )

            # Verify DataFrame creation
            mock_pl.DataFrame.assert_called_once()
            assert result == mock_df_with_columns

    def test_fetch_day_df_with_force(self):
        """Test fetch_day_df with force parameter."""
        mock_pl = Mock()
        mock_df = Mock()
        mock_df_with_columns = Mock()

        # Mock DataFrame columns properly
        mock_df.columns = [
            "asx_code",
            "company_name",
            "short_sold",
            "issued_shares",
            "percent_short",
            "report_date",
        ]
        mock_df.__contains__ = Mock(
            return_value=False
        )  # No expected columns in this case

        mock_pl.DataFrame.return_value = mock_df
        mock_df.with_columns.return_value = mock_df_with_columns

        # Mock polars column operations
        expr = Mock()
        expr.str.to_date.return_value = "date_col"
        expr_after_cast = Mock()
        expr.cast.return_value = expr_after_cast
        expr_after_cast.dt.date.return_value = "report_date_col"
        mock_pl.col.return_value = expr
        mock_pl.Datetime = Mock(return_value="ms_dt")
        mock_pl.Int64 = "Int64"
        mock_pl.Float64 = "Float64"
        mock_pl.Date = "Date"
        mock_df.schema = {"report_date": "Utf8"}

        self.mock_client.fetch_day.return_value = self.sample_fetch_result

        with patch("asxshorts.adapters.pl", mock_pl):
            adapter = PolarsAdapter(self.mock_client)
            result = adapter.fetch_day_df(self.test_date, force=True)

            self.mock_client.fetch_day.assert_called_once_with(
                self.test_date, force=True
            )
            assert result == mock_df_with_columns

    def test_fetch_range_df_success(self):
        """Test successful fetch_range_df operation."""
        # Setup range result with correct field names
        range_result = RangeResult(
            start_date=date(2023, 12, 1),
            end_date=date(2023, 12, 15),
            total_records=2,
            successful_dates=[self.test_date],
            failed_dates=[],
            total_fetch_time_ms=200.0,
            results={self.test_date: self.sample_fetch_result},
        )

        mock_pl = Mock()
        mock_df = Mock()
        mock_df_with_columns = Mock()

        # Mock DataFrame columns properly
        mock_df.columns = [
            "asx_code",
            "company_name",
            "short_sold",
            "issued_shares",
            "percent_short",
            "report_date",
        ]
        mock_df.__contains__ = Mock(
            return_value=False
        )  # No expected columns in this case

        mock_pl.DataFrame.return_value = mock_df
        mock_df.with_columns.return_value = mock_df_with_columns

        # Mock polars column operations
        expr = Mock()
        expr.str.to_date.return_value = "date_col"
        expr_after_cast = Mock()
        expr.cast.return_value = expr_after_cast
        expr_after_cast.dt.date.return_value = "report_date_col"
        mock_pl.col.return_value = expr
        mock_pl.Datetime = Mock(return_value="ms_dt")
        mock_pl.Int64 = "Int64"
        mock_pl.Float64 = "Float64"
        mock_pl.Date = "Date"
        mock_df.schema = {"report_date": "Utf8"}

        self.mock_client.fetch_range.return_value = range_result

        with patch("asxshorts.adapters.pl", mock_pl):
            adapter = PolarsAdapter(self.mock_client)
            result = adapter.fetch_range_df(date(2023, 12, 1), date(2023, 12, 15))

            # Verify client was called correctly
            self.mock_client.fetch_range.assert_called_once_with(
                date(2023, 12, 1), date(2023, 12, 15), force=False
            )

            # Verify DataFrame creation
            mock_pl.DataFrame.assert_called_once()
            assert result == mock_df_with_columns

    def test_records_to_dataframe_empty(self):
        """Test _records_to_dataframe with empty records."""
        mock_pl = Mock()
        mock_df = Mock()
        mock_pl.DataFrame.return_value = mock_df
        mock_pl.Date = "Date"
        mock_pl.Utf8 = "Utf8"
        mock_pl.Int64 = "Int64"
        mock_pl.Float64 = "Float64"

        with patch("asxshorts.adapters.pl", mock_pl):
            adapter = PolarsAdapter(self.mock_client)
            result = adapter._records_to_dataframe([])

            # Should create DataFrame with expected schema for empty case
            expected_schema = {
                "date": "Date",
                "product": "Utf8",
                "short_qty": "Int64",
                "total_qty": "Int64",
                "short_pct": "Float64",
            }
            mock_pl.DataFrame.assert_called_once_with(schema=expected_schema)
            assert result == mock_df

    def test_records_to_dataframe_with_data(self):
        """Test _records_to_dataframe with actual records."""
        mock_pl = Mock()
        mock_df = Mock()
        mock_df_with_columns = Mock()

        # Mock DataFrame columns properly - simulate having expected columns
        mock_df.columns = ["date", "short_qty", "total_qty", "short_pct"]
        mock_df.__contains__ = Mock(
            side_effect=lambda x: x in ["date", "short_qty", "total_qty", "short_pct"]
        )

        mock_pl.DataFrame.return_value = mock_df
        mock_df.with_columns.return_value = mock_df_with_columns

        # Mock polars column operations
        expr = Mock()
        expr.str.to_date.return_value = "date_col"
        expr_after_cast = Mock()
        expr.cast.return_value = expr_after_cast
        expr_after_cast.dt.date.return_value = "report_date_col"
        mock_pl.col.return_value = expr
        mock_pl.Datetime = Mock(return_value="ms_dt")
        mock_pl.Int64 = "Int64"
        mock_pl.Float64 = "Float64"
        mock_pl.Date = "Date"
        mock_df.schema = {
            "date": "Utf8",
            "short_qty": "Int64",
            "total_qty": "Int64",
            "short_pct": "Float64",
        }

        with patch("asxshorts.adapters.pl", mock_pl):
            adapter = PolarsAdapter(self.mock_client)
            records_dict = [record.model_dump() for record in self.sample_records]
            result = adapter._records_to_dataframe(records_dict)

            # Verify DataFrame creation with record data
            mock_pl.DataFrame.assert_called_once_with(records_dict)
            assert result == mock_df_with_columns


class TestAdapterFactoryFunctions:
    """Test cases for adapter factory functions."""

    def test_create_pandas_adapter_with_client(self):
        """Test create_pandas_adapter with provided client."""
        mock_client = Mock(spec=ShortsClient)

        with patch("asxshorts.adapters.PandasAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter

            result = create_pandas_adapter(client=mock_client)

            mock_adapter_class.assert_called_once_with(mock_client)
            assert result == mock_adapter

    def test_create_pandas_adapter_without_client(self):
        """Test create_pandas_adapter without provided client."""
        with patch("asxshorts.adapters.ShortsClient") as mock_client_class:
            with patch("asxshorts.adapters.PandasAdapter") as mock_adapter_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_adapter = Mock()
                mock_adapter_class.return_value = mock_adapter

                result = create_pandas_adapter()

                mock_client_class.assert_called_once()
                mock_adapter_class.assert_called_once_with(mock_client)
                assert result == mock_adapter

    def test_create_polars_adapter_with_client(self):
        """Test create_polars_adapter with provided client."""
        mock_client = Mock(spec=ShortsClient)

        with patch("asxshorts.adapters.PolarsAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter

            result = create_polars_adapter(client=mock_client)

            mock_adapter_class.assert_called_once_with(mock_client)
            assert result == mock_adapter

    def test_create_polars_adapter_without_client(self):
        """Test create_polars_adapter without provided client."""
        with patch("asxshorts.adapters.ShortsClient") as mock_client_class:
            with patch("asxshorts.adapters.PolarsAdapter") as mock_adapter_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_adapter = Mock()
                mock_adapter_class.return_value = mock_adapter

                result = create_polars_adapter()

                mock_client_class.assert_called_once()
                mock_adapter_class.assert_called_once_with(mock_client)
                assert result == mock_adapter


class TestAdapterIntegration:
    """Integration tests for adapters."""

    def test_pandas_adapter_data_flow(self):
        """Test complete data flow through PandasAdapter."""
        mock_client = Mock(spec=ShortsClient)
        test_date = date(2023, 12, 15)

        # Create test record with all required fields
        test_record = ShortRecord(
            report_date=test_date,
            asx_code="TEST",
            company_name="Test Company",
            short_sold=5000,
            issued_shares=50000,
            percent_short=10.0,
            raw={"PRODUCT": "TEST", "SHORT QTY": "5000"},
        )

        fetch_result = FetchResult(
            fetch_date=test_date,
            record_count=1,
            from_cache=False,
            fetch_time_ms=150.0,
            url="https://example.com/test.csv",
            records=[test_record],
        )

        mock_client.fetch_day.return_value = fetch_result
        mock_pd = Mock()
        mock_df = Mock()

        # Mock DataFrame columns properly
        mock_df.columns = [
            "asx_code",
            "company_name",
            "short_sold",
            "issued_shares",
            "percent_short",
            "report_date",
        ]
        mock_df.__contains__ = Mock(return_value=False)
        mock_df.__getitem__ = Mock(return_value=Mock())
        mock_df.__setitem__ = Mock()

        mock_pd.DataFrame.return_value = mock_df
        mock_pd.to_datetime = Mock()
        mock_pd.to_numeric = Mock()

        with patch("asxshorts.adapters.pd", mock_pd):
            adapter = PandasAdapter(mock_client)
            result = adapter.fetch_day_df(test_date)

            # Verify the complete flow
            mock_client.fetch_day.assert_called_once_with(test_date, force=False)
            mock_pd.DataFrame.assert_called_once()

            assert result == mock_df

    def test_polars_adapter_data_flow(self):
        """Test complete data flow through PolarsAdapter."""
        mock_client = Mock(spec=ShortsClient)
        test_date = date(2023, 12, 15)

        # Create test record with all required fields
        test_record = ShortRecord(
            report_date=test_date,
            asx_code="TEST",
            company_name="Test Company",
            short_sold=5000,
            issued_shares=50000,
            percent_short=10.0,
            raw={"PRODUCT": "TEST", "SHORT QTY": "5000"},
        )

        fetch_result = FetchResult(
            fetch_date=test_date,
            record_count=1,
            from_cache=False,
            fetch_time_ms=150.0,
            url="https://example.com/test.csv",
            records=[test_record],
        )

        mock_client.fetch_day.return_value = fetch_result
        mock_pl = Mock()
        mock_df = Mock()
        mock_df_with_columns = Mock()

        # Mock DataFrame columns properly
        mock_df.columns = [
            "asx_code",
            "company_name",
            "short_sold",
            "issued_shares",
            "percent_short",
            "report_date",
        ]
        mock_df.__contains__ = Mock(
            return_value=False
        )  # No expected columns in this case

        mock_pl.DataFrame.return_value = mock_df
        mock_df.with_columns.return_value = mock_df_with_columns

        # Mock polars column operations
        expr = Mock()
        expr.str.to_date.return_value = "date_col"
        expr_after_cast = Mock()
        expr.cast.return_value = expr_after_cast
        expr_after_cast.dt.date.return_value = "report_date_col"
        mock_pl.col.return_value = expr
        mock_pl.Datetime = Mock(return_value="ms_dt")
        mock_pl.Int64 = "Int64"
        mock_pl.Float64 = "Float64"
        mock_pl.Date = "Date"
        mock_df.schema = {"report_date": "Utf8"}

        with patch("asxshorts.adapters.pl", mock_pl):
            adapter = PolarsAdapter(mock_client)
            result = adapter.fetch_day_df(test_date)

            # Verify the complete flow
            mock_client.fetch_day.assert_called_once_with(test_date, force=False)
            mock_pl.DataFrame.assert_called_once()

            assert result == mock_df_with_columns

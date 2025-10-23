"""Extra coverage tests for optional adapters and helpers."""

import importlib
import sys
from types import ModuleType
from unittest.mock import Mock, patch

import pytest


def test_package_init_without_optional_adapters(monkeypatch):
    """Reload package when optional adapters are unavailable."""
    # Create a dummy adapters module missing expected symbols so import fails
    dummy = ModuleType("asxshorts.adapters")
    original = sys.modules.get("asxshorts.adapters")
    monkeypatch.setitem(sys.modules, "asxshorts.adapters", dummy)

    # Reload top-level package to exercise try/except blocks
    import asxshorts as pkg

    pkg = importlib.reload(pkg)

    # Neither optional adapter names should be exported
    assert "PandasAdapter" not in pkg.__all__
    assert "PolarsAdapter" not in pkg.__all__

    # Restore real adapters module and reload so other tests see normal exports
    if original is not None:
        sys.modules["asxshorts.adapters"] = original
        importlib.reload(pkg)


def test_to_pandas_import_guard():
    from asxshorts import adapters

    with patch.object(adapters, "pd", None):
        with pytest.raises(ImportError):
            adapters.to_pandas([])


def test_to_pandas_with_data():
    from asxshorts import adapters

    mock_pd = Mock()
    mock_df = Mock()
    mock_pd.DataFrame.return_value = mock_df
    mock_df.columns = ["date", "short_qty", "total_qty", "short_pct"]
    mock_df.__getitem__ = Mock(return_value=Mock())
    mock_df.__setitem__ = Mock()

    with patch.object(adapters, "pd", mock_pd):
        out = adapters.to_pandas(
            [
                {
                    "date": "2024-01-02",
                    "short_qty": "10",
                    "total_qty": 100,
                    "short_pct": "0.1",
                }
            ]
        )
        assert out is mock_df
        mock_pd.DataFrame.assert_called_once()
        mock_pd.to_datetime.assert_called()
        mock_pd.to_numeric.assert_called()


def test_to_polars_import_guard():
    from asxshorts import adapters

    with patch.object(adapters, "pl", None):
        with pytest.raises(ImportError):
            adapters.to_polars([])


def test_to_polars_with_data():
    from asxshorts import adapters

    mock_pl = Mock()
    mock_df = Mock()
    mock_df_with_columns = Mock()
    mock_pl.DataFrame.return_value = mock_df
    mock_df.with_columns.return_value = mock_df_with_columns

    # Simulate presence of all expected columns
    mock_df.columns = [
        "date",
        "report_date",
        "short_qty",
        "total_qty",
        "short_pct",
        "short_sold",
        "issued_shares",
        "percent_short",
    ]

    # Mock polars column operations to return simple sentinels
    expr = Mock()
    expr.str.to_date.return_value = "date_expr"
    expr_after_cast = Mock()
    expr.cast.return_value = expr_after_cast
    expr_after_cast.dt.date.return_value = "report_date_expr"
    mock_pl.col.return_value = expr
    mock_pl.Datetime = Mock(return_value="ms_dt")
    mock_pl.Int64 = "Int64"
    mock_pl.Float64 = "Float64"
    mock_pl.Date = "Date"
    # Schema should be subscriptable and return non-Date types to trigger conversions
    mock_df.schema = {
        "date": "Utf8",
        "report_date": "Utf8",
        "short_qty": "Int64",
        "total_qty": "Int64",
        "short_pct": "Float64",
        "short_sold": "Int64",
        "issued_shares": "Int64",
        "percent_short": "Float64",
    }

    with patch.object(adapters, "pl", mock_pl):
        out = adapters.to_polars(
            [
                {
                    "date": "2024-01-02",
                    "report_date": "2024-01-02",
                    "short_qty": "10",
                    "total_qty": 100,
                    "short_pct": "0.1",
                    "short_sold": 5,
                    "issued_shares": "200",
                    "percent_short": 0.5,
                }
            ]
        )
        assert out is mock_df_with_columns
        mock_pl.DataFrame.assert_called_once()
        # Ensure we attempted to add expressions
        mock_df.with_columns.assert_called()

"""Exercise conversion contracts with real optional DataFrame libraries."""

from copy import deepcopy
from datetime import date
from unittest.mock import Mock

import pytest

from asxshorts.adapters import PandasAdapter, PolarsAdapter, to_pandas, to_polars
from asxshorts.models import FetchResult, ShortRecord


@pytest.mark.parametrize("library", ["pandas", "polars"])
def test_conversion_preserves_values_and_input(library):
    module = pytest.importorskip(library)
    convert = to_pandas if library == "pandas" else to_polars
    records = [
        {
            "report_date": "2024-01-15",
            "asx_code": "ABC",
            "short_sold": "12",
            "issued_shares": "100",
            "percent_short": "12.0",
        },
        {
            "report_date": "2024-01-16",
            "asx_code": "DEF",
            "short_sold": "-",
            "issued_shares": "",
            "percent_short": None,
        },
    ]
    original = deepcopy(records)

    frame = convert(records)

    assert records == original
    assert list(frame["asx_code"]) == ["ABC", "DEF"]
    for column, expected in (
        ("short_sold", 12),
        ("issued_shares", 100),
        ("percent_short", 12.0),
    ):
        assert frame[column][0] == expected
        if library == "pandas":
            assert module.isna(frame[column][1])
        else:
            assert frame[column][1] is None
    actual_date = frame["report_date"][0]
    assert (actual_date.date() if library == "pandas" else actual_date) == date(
        2024, 1, 15
    )


@pytest.mark.parametrize("library", ["pandas", "polars"])
def test_fetch_adapter_matches_model_conversion(library):
    pytest.importorskip(library)
    record = ShortRecord(
        report_date=date(2024, 1, 15),
        asx_code="ABC",
        short_sold=12,
        issued_shares=100,
        percent_short=12.0,
    )
    client = Mock()
    client.fetch_day.return_value = FetchResult(
        fetch_date=record.report_date,
        record_count=1,
        from_cache=True,
        fetch_time_ms=0,
        records=[record],
    )
    adapter = PandasAdapter(client) if library == "pandas" else PolarsAdapter(client)
    convert = to_pandas if library == "pandas" else to_polars

    actual = adapter.fetch_day_df(record.report_date, force=True)

    assert actual.equals(convert([record]))
    client.fetch_day.assert_called_once_with(record.report_date, force=True)

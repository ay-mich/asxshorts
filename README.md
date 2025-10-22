# asxshorts

[![PyPI version](https://badge.fury.io/py/asxshorts.svg)](https://badge.fury.io/py/asxshorts)
[![Python versions](https://img.shields.io/pypi/pyversions/asxshorts.svg)](https://pypi.org/project/asxshorts/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/ay-mich/asxshorts/workflows/CI/badge.svg)](https://github.com/ay-mich/asxshorts/actions)

Lightweight Python client to download official ASIC short position daily CSVs across a date range, with local caching.

## Features

- 🚀 **Simple API**: Fetch short selling data with just a few lines of code
- 💾 **Local Caching**: Automatic file-based caching with atomic operations
- 🔄 **Retry Logic**: Built-in exponential backoff for robust data fetching
- 📊 **Multiple Formats**: Typed models + dicts, optional pandas/polars adapters
- 🖥️ **CLI Interface**: Command-line tool for quick data access
- 🛡️ **Type Safe**: Full type hints and mypy compatibility
- ⚡ **Minimal Dependencies**: Only requires `requests`, `python-dateutil`, and `typer`

## Installation

```bash
# Basic installation
pip install asxshorts

# With pandas support
pip install asxshorts[pandas]

# With polars support
pip install asxshorts[polars]

# Development installation
pip install asxshorts[dev]
```

## Quick Start

### Python API

```python
from datetime import date
from asxshorts import ShortsClient

# Create client
client = ShortsClient()

# Fetch data for a specific date
res = client.fetch_day(date(2024, 1, 15))
print(f"Found {res.record_count} records (from_cache={res.from_cache})")

# Fetch data for a date range
rng = client.fetch_range(
    start=date(2024, 1, 15),
    end=date(2024, 1, 19)
)
print(f"Total records: {rng.total_records}")

# Each record is a dictionary with normalized fields
for record in res.records[:3]:
    d = record.report_date
    print(f"{d}: {record.asx_code} - {record.percent_short}")
```

### Pandas Integration

```python
from asxshorts.adapters import create_pandas_adapter, to_pandas

# Create pandas adapter
adapter = create_pandas_adapter()

# Fetch as DataFrame via adapter
df = adapter.fetch_day_df(date(2024, 1, 15))
print(df.head())

# Or convert existing records
df2 = to_pandas([r.model_dump() for r in res.records])

# Date range as DataFrame
df = adapter.fetch_range_df(
    start=date(2024, 1, 15),
    end=date(2024, 1, 19)
)
```

### Polars Integration

```python
from asxshorts.adapters import create_polars_adapter, to_polars

# Create polars adapter
adapter = create_polars_adapter()

# Fetch as Polars DataFrame
df = adapter.fetch_day_df(date(2024, 1, 15))
print(df.head())

# Or convert existing records
df2 = to_polars([r.model_dump() for r in res.records])
```

### Command Line Interface

```bash
# Fetch data for a specific date
asxshorts fetch 2024-01-15

# Fetch yesterday's data
asxshorts fetch yesterday

# Fetch date range and save to file
asxshorts range 2024-01-15 2024-01-19 --output data.json

# Show cache statistics
asxshorts cache stats

# Clear cache
asxshorts cache clear

# Clean up old cache files
asxshorts cache cleanup --max-age 30
```

## Configuration

### Environment Variables

```bash
# Custom cache directory
export asxshorts_CACHE_DIR="/path/to/cache"

# Custom base URL
export asxshorts_BASE_URL="https://download.asic.gov.au"

# Custom user agent
export asxshorts_USER_AGENT="MyApp/1.0"
```

### Client Configuration

```python
from asxshorts import ShortsClient

client = ShortsClient(
    cache_dir="/custom/cache/path",
    timeout=30.0,
    retries=5,
    backoff=1.0
)
```

## Data Format

Each record contains the following normalized fields:

```python
{
    "report_date": "2024-01-15",   # date
    "asx_code": "ABC",            # ASX code
    "company_name": "…",          # optional
    "short_sold": 1000000,         # int
    "issued_shares": 10000000,     # int
    "percent_short": 10.0          # float
}
```

## Caching

- Files are cached in `~/.cache/asxshorts/` by default
- Cache uses atomic writes with file locking for thread safety
- Cached files are named by date: `2024-01-15.csv`
- Use `force=True` to bypass cache and fetch fresh data

## Error Handling

```python
from asxshorts import ShortsClient
from asxshorts.errors import NotFoundError, FetchError, RateLimitError

client = ShortsClient()

try:
    records = client.fetch_day(date(2024, 1, 15))
except NotFoundError:
    print("No data available for this date")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after} seconds")
except FetchError as e:
    print(f"Failed to fetch data: {e}")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

---

**Note**: This package resolves daily CSV URLs via the official ASIC short-selling index. Please respect ASIC/ASX terms and usage limits.

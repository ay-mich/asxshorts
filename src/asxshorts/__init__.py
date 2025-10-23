"""ASX Shorts - Fetch official ASX short selling data with local caching."""

__version__ = "0.1.1"

from .client import ShortsClient
from .errors import (
    CacheError,
    FetchError,
    NotFoundError,
    ParseError,
    RateLimitError,
)

# Optional adapters (imported on demand)
try:
    from .adapters import PandasAdapter, create_pandas_adapter  # noqa: F401

    __all_pandas__ = ["PandasAdapter", "create_pandas_adapter"]
except ImportError:
    __all_pandas__ = []

try:
    from .adapters import PolarsAdapter, create_polars_adapter  # noqa: F401

    __all_polars__ = ["PolarsAdapter", "create_polars_adapter"]
except ImportError:
    __all_polars__ = []

__all__ = [
    "ShortsClient",
    "FetchError",
    "NotFoundError",
    "RateLimitError",
    "ParseError",
    "CacheError",
    *__all_pandas__,
    *__all_polars__,
]

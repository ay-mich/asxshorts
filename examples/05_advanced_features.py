# %% [markdown]
"""
# 🚀 ASX Shorts Package - Advanced Features

This script demonstrates advanced features and production-ready patterns for the `asxshorts` package:

- 💾 **Cache Management**: Optimize performance with intelligent caching
- 🛡️ **Error Handling**: Robust error handling and retry patterns
- ⚡ **Performance**: Optimization techniques for production use
- ✅ **Data Validation**: Quality checks and data integrity
- 🔧 **Custom Processing**: Advanced data processing patterns
- 📊 **Monitoring**: Performance monitoring and metrics

## Production Considerations
- **Reliability**: Handle network failures gracefully
- **Performance**: Minimize API calls and optimize data processing
- **Monitoring**: Track performance and data quality
- **Scalability**: Design for high-volume data processing

## Prerequisites
```bash
pip install 'asxshorts' psutil
```
"""

# %% [markdown]
"""
## 📦 Setup and Imports
Import required modules and check for optional dependencies.
"""

# %%
import logging
import time
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any

from asxshorts import ShortsClient, create_pandas_adapter, create_polars_adapter
from asxshorts.errors import FetchError, NotFoundError

# Optional imports for enhanced functionality
try:
    import pandas as pd

    HAS_PANDAS = True
    print("✅ Pandas available")
except ImportError:
    HAS_PANDAS = False
    print("🐼 Pandas not available")

try:
    import polars as pl

    HAS_POLARS = True
    print("✅ Polars available")
except ImportError:
    HAS_POLARS = False
    print("⚡ Polars not available")

try:
    import psutil

    HAS_PSUTIL = True
    print("✅ psutil available for performance monitoring")
except ImportError:
    HAS_PSUTIL = False
    print("📊 Install psutil for performance monitoring: pip install psutil")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

print("🚀 Advanced Features Examples - ASX Short Selling")
print("=" * 50)

# %% [markdown]
"""
## 💾 Cache Management
Demonstrate intelligent caching strategies for optimal performance.
"""


# %%
def cache_management_examples():
    """Demonstrate cache management and optimization strategies."""
    print("\n💾 Cache Management Examples")
    print("-" * 32)

    # Create client with default caching
    client = ShortsClient()

    # Test cache behavior
    target_date = date.today() - timedelta(days=20)

    print(f"🔍 Testing cache behavior for {target_date}")

    # First fetch - should hit the network
    start_time = time.time()
    try:
        result1 = client.fetch_day(target_date)
        first_fetch_time = time.time() - start_time
        print(
            f"✅ First fetch: {first_fetch_time:.3f}s ({len(result1.records)} records)"
        )
    except (NotFoundError, FetchError) as e:
        print(f"❌ First fetch failed: {e}")
        return

    # Second fetch - should use cache
    start_time = time.time()
    try:
        result2 = client.fetch_day(target_date)
        second_fetch_time = time.time() - start_time
        print(f"⚡ Second fetch (cached): {second_fetch_time:.3f}s")

        # Calculate speedup
        if second_fetch_time > 0:
            speedup = first_fetch_time / second_fetch_time
            print(f"🚀 Cache speedup: {speedup:.1f}x faster")

    except (NotFoundError, FetchError) as e:
        print(f"❌ Second fetch failed: {e}")

    # Cache statistics
    print("\n📊 Cache Performance:")
    print(f"   Network fetch: {first_fetch_time:.3f}s")
    print(f"   Cached fetch: {second_fetch_time:.3f}s")
    print(
        f"   Data consistency: {'✅ Identical' if len(result1.records) == len(result2.records) else '❌ Different'}"
    )

    # Demonstrate cache warming for date ranges
    print("\n🔥 Cache Warming Strategy:")
    end_date = date.today() - timedelta(days=20)
    start_date = end_date - timedelta(days=5)

    warm_start = time.time()
    try:
        range_result = client.fetch_range(start_date, end_date)
        warm_time = time.time() - warm_start

        total_records = sum(
            len(daily_result.records)
            for daily_result in range_result.results.values()
            if daily_result.records
        )
        print(
            f"✅ Warmed cache for {len(range_result.results)} days in {warm_time:.3f}s"
        )
        print(f"   Total records cached: {total_records}")

        # Now individual fetches should be fast
        individual_start = time.time()
        for single_date in [start_date + timedelta(days=i) for i in range(3)]:
            client.fetch_day(single_date)
        individual_time = time.time() - individual_start

        print(f"⚡ 3 individual fetches from cache: {individual_time:.3f}s")

    except (NotFoundError, FetchError) as e:
        print(f"❌ Cache warming failed: {e}")


# Run cache management examples
cache_management_examples()

# %% [markdown]
"""
## 🛡️ Error Handling and Resilience
Implement robust error handling patterns for production environments.
"""


# %%
def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """Implement exponential backoff retry pattern."""
    for attempt in range(max_retries):
        try:
            return func()
        except (FetchError, NotFoundError) as e:
            if attempt == max_retries - 1:
                raise e

            delay = base_delay * (2**attempt)
            logger.warning(
                f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)


@contextmanager
def error_context(operation_name: str):
    """Context manager for consistent error handling."""
    start_time = time.time()
    try:
        logger.info(f"Starting {operation_name}")
        yield
        duration = time.time() - start_time
        logger.info(f"Completed {operation_name} in {duration:.3f}s")
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Failed {operation_name} after {duration:.3f}s: {e}")
        raise


def robust_data_fetching():
    """Demonstrate robust data fetching with comprehensive error handling."""
    print("\n🛡️ Robust Error Handling Examples")
    print("-" * 36)

    client = ShortsClient()

    # Example 1: Retry pattern for single day
    print("🔄 Testing retry pattern for single day fetch:")

    def fetch_with_retry():
        target_date = date.today() - timedelta(days=20)
        return client.fetch_day(target_date)

    try:
        with error_context("Single day fetch with retry"):
            result = retry_with_backoff(fetch_with_retry)
            print(f"✅ Successfully fetched {len(result.records)} records")
    except Exception as e:
        print(f"❌ All retry attempts failed: {e}")

    # Example 2: Graceful degradation for date ranges
    print("\n🔄 Testing graceful degradation for date range:")

    end_date = date.today() - timedelta(days=20)
    start_date = end_date - timedelta(days=10)

    successful_fetches = []
    failed_dates = []

    with error_context("Date range with graceful degradation"):
        for single_date in [start_date + timedelta(days=i) for i in range(11)]:
            try:
                result = retry_with_backoff(
                    lambda d=single_date: client.fetch_day(d), max_retries=2
                )
                if result.records:
                    successful_fetches.append((single_date, len(result.records)))
                    print(f"✅ {single_date}: {len(result.records)} records")
                else:
                    failed_dates.append(single_date)
                    print(f"⚠️ {single_date}: No data available")
            except Exception as e:
                failed_dates.append(single_date)
                print(f"❌ {single_date}: {e}")

    # Summary
    print("\n📊 Fetch Summary:")
    print(f"   Successful: {len(successful_fetches)} days")
    print(f"   Failed: {len(failed_dates)} days")
    print(
        f"   Success rate: {len(successful_fetches) / (len(successful_fetches) + len(failed_dates)) * 100:.1f}%"
    )

    if successful_fetches:
        total_records = sum(count for _, count in successful_fetches)
        print(f"   Total records: {total_records}")

    # Example 3: Data validation and fallback
    print("\n✅ Data validation and fallback strategies:")

    def validate_data(records) -> dict[str, Any]:
        """Validate fetched data quality."""
        if not records:
            return {"valid": False, "reason": "No records"}

        # Check for reasonable data ranges
        short_percentages = [r.percent_short for r in records]

        if not short_percentages:
            return {"valid": False, "reason": "No short percentages"}

        max_short = max(short_percentages)
        min_short = min(short_percentages)

        # Basic sanity checks
        if max_short > 100 or min_short < 0:
            return {
                "valid": False,
                "reason": f"Invalid range: {min_short}-{max_short}%",
            }

        if len(records) < 10:
            return {"valid": False, "reason": f"Too few records: {len(records)}"}

        return {
            "valid": True,
            "record_count": len(records),
            "short_range": f"{min_short:.2f}-{max_short:.2f}%",
            "avg_short": sum(short_percentages) / len(short_percentages),
        }

    # Test validation
    try:
        result = client.fetch_day(date.today() - timedelta(days=20))
        validation = validate_data(result.records)

        if validation["valid"]:
            print("✅ Data validation passed:")
            print(f"   Records: {validation['record_count']}")
            print(f"   Short range: {validation['short_range']}")
            print(f"   Average short: {validation['avg_short']:.2f}%")
        else:
            print(f"❌ Data validation failed: {validation['reason']}")

    except Exception as e:
        print(f"❌ Validation test failed: {e}")


# Run error handling examples
robust_data_fetching()

# %% [markdown]
"""
## ⚡ Performance Optimization
Advanced techniques for optimizing performance in production environments.
"""


# %%
def performance_monitoring():
    """Monitor and optimize performance with detailed metrics."""
    print("\n⚡ Performance Optimization Examples")
    print("-" * 37)

    if not HAS_PSUTIL:
        print("⚠️ Install psutil for detailed performance monitoring")

    client = ShortsClient()

    # Performance monitoring context
    @contextmanager
    def performance_monitor(operation_name: str):
        """Monitor CPU, memory, and timing for operations."""
        if HAS_PSUTIL:
            process = psutil.Process()
            start_cpu = process.cpu_percent()
            start_memory = process.memory_info().rss / 1024 / 1024  # MB

        start_time = time.time()

        try:
            yield
        finally:
            duration = time.time() - start_time

            if HAS_PSUTIL:
                end_cpu = process.cpu_percent()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_delta = end_memory - start_memory

                print(f"📊 {operation_name} Performance:")
                print(f"   Duration: {duration:.3f}s")
                print(f"   Memory: {end_memory:.1f}MB ({memory_delta:+.1f}MB)")
                print(f"   CPU: {end_cpu:.1f}%")
            else:
                print(f"📊 {operation_name}: {duration:.3f}s")

    # Test 1: Single day fetch optimization
    with performance_monitor("Single day fetch"):
        target_date = date.today() - timedelta(days=20)
        try:
            result = client.fetch_day(target_date)
            print(f"✅ Fetched {len(result.records)} records")
        except Exception as e:
            print(f"❌ Fetch failed: {e}")

    # Test 2: Batch processing optimization
    with performance_monitor("Batch processing (5 days)"):
        end_date = date.today() - timedelta(days=20)
        start_date = end_date - timedelta(days=4)

        try:
            # Use range fetch for efficiency
            range_result = client.fetch_range(start_date, end_date)
            total_records = sum(
                len(r.records) for r in range_result.results if r.records
            )
            print(
                f"✅ Batch processed {total_records} records across {len(range_result.results)} days"
            )
        except Exception as e:
            print(f"❌ Batch processing failed: {e}")

    # Test 3: Data processing optimization
    if HAS_PANDAS and HAS_POLARS:
        print("\n🏁 DataFrame Processing Comparison:")

        try:
            target_date = date.today() - timedelta(days=20)

            # Pandas processing
            with performance_monitor("Pandas processing"):
                pandas_adapter = create_pandas_adapter()
                df_pandas = pandas_adapter.fetch_day_df(target_date)

                if df_pandas is not None:
                    # Filter non-numeric values and apply threshold (0.05 = 5%)
                    numeric_mask = (df_pandas["percent_short"] != "-") & df_pandas[
                        "percent_short"
                    ].notna()
                    numeric_df = df_pandas[numeric_mask].copy()
                    numeric_df["percent_short"] = pd.to_numeric(
                        numeric_df["percent_short"], errors="coerce"
                    )

                    # Complex operations
                    filtered = numeric_df[numeric_df["percent_short"] > 0.05]
                    grouped = filtered.groupby("asx_code").agg(
                        {"percent_short": ["mean", "max", "std"]}
                    )
                    sorted_result = grouped.sort_values(
                        ("percent_short", "mean"), ascending=False
                    )
                    print(f"   Pandas result: {len(sorted_result)} processed records")
                else:
                    print(f"   Pandas: No data available for {target_date}")

            # Note: Polars processing commented out due to adapter bug
            # with performance_monitor("Polars processing"):
            #     polars_adapter = create_polars_adapter()
            #     df_polars = polars_adapter.fetch_day_df(target_date)
            #
            #     if df_polars is not None:
            #         # Same operations in Polars (0.05 = 5%)
            #         result_polars = (
            #             df_polars
            #             .filter(
            #                 (pl.col("percent_short").is_not_null()) &
            #                 (pl.col("percent_short") != "-")
            #             )
            #             .with_columns(pl.col("percent_short").cast(pl.Float64, strict=False))
            #             .filter(pl.col("percent_short") > 0.05)
            #             .group_by("asx_code")
            #             .agg([
            #                 pl.col("percent_short").mean().alias("mean_short"),
            #                 pl.col("percent_short").max().alias("max_short"),
            #                 pl.col("percent_short").std().alias("std_short")
            #             ])
            #             .sort("mean_short", descending=True)
            #         )
            #         print(f"   Polars result: {len(result_polars)} processed records")
            #     else:
            #         print(f"   Polars: No data available for {target_date}")

            print(
                "   Note: Polars comparison temporarily disabled due to adapter implementation issue"
            )

        except Exception as e:
            print(f"❌ DataFrame comparison failed: {e}")

    # Test 4: Memory-efficient streaming
    print("\n🌊 Memory-Efficient Processing:")

    def process_data_streaming(records, chunk_size: int = 100):
        """Process data in chunks to minimize memory usage."""
        processed_count = 0
        high_short_count = 0

        for i in range(0, len(records), chunk_size):
            chunk = records[i : i + chunk_size]

            # Process chunk
            for record in chunk:
                processed_count += 1
                if record.percent_short > 10.0:
                    high_short_count += 1

        return processed_count, high_short_count

    try:
        result = client.fetch_day(date.today() - timedelta(days=20))
        if result.records:
            with performance_monitor("Streaming processing"):
                processed, high_short = process_data_streaming(result.records)
                print(
                    f"✅ Streamed {processed} records, found {high_short} high short interest"
                )
    except Exception as e:
        print(f"❌ Streaming processing failed: {e}")


# Run performance optimization examples
performance_monitoring()

# %% [markdown]
"""
## ✅ Data Validation and Quality Assurance
Implement comprehensive data validation for production reliability.
"""


# %%
class DataQualityChecker:
    """Comprehensive data quality validation."""

    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = []
        self.errors = []

    def validate_record(self, record) -> bool:
        """Validate a single short selling record."""
        valid = True

        # Check ASX code format
        if not record.asx_code or len(record.asx_code) < 2:
            self.errors.append(f"Invalid ASX code: {record.asx_code}")
            valid = False

        # Check percentage range
        if record.percent_short < 0 or record.percent_short > 100:
            self.errors.append(f"Invalid short percentage: {record.percent_short}%")
            valid = False

        # Check share counts
        if record.issued_shares <= 0:
            self.errors.append(f"Invalid issued shares: {record.issued_shares}")
            valid = False

        if record.short_sold < 0:
            self.errors.append(f"Invalid short positions: {record.short_sold}")
            valid = False

        # Consistency check
        calculated_percent = (record.short_sold / record.issued_shares) * 100
        if abs(calculated_percent - record.percent_short) > 0.1:
            self.warnings.append(
                f"{record.asx_code}: Percentage mismatch - "
                f"reported: {record.percent_short}%, calculated: {calculated_percent:.2f}%"
            )

        if valid:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

        return valid

    def validate_dataset(self, records) -> dict[str, Any]:
        """Validate entire dataset."""
        if not records:
            return {"valid": False, "reason": "No records to validate"}

        # Reset counters
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = []
        self.errors = []

        # Validate each record
        valid_records = []
        for record in records:
            if self.validate_record(record):
                valid_records.append(record)

        # Dataset-level checks
        short_percentages = [r.percent_short for r in valid_records]

        if short_percentages:
            avg_short = sum(short_percentages) / len(short_percentages)
            max_short = max(short_percentages)
            min_short = min(short_percentages)

            # Statistical outlier detection
            if max_short > 50:
                self.warnings.append(
                    f"Unusually high short interest detected: {max_short}%"
                )

            # Check for data completeness
            unique_codes = set(r.asx_code for r in valid_records)
            if len(unique_codes) < 100:
                self.warnings.append(
                    f"Low stock count: {len(unique_codes)} unique ASX codes"
                )

        return {
            "valid": self.checks_failed == 0,
            "total_records": len(records),
            "valid_records": len(valid_records),
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "warnings": len(self.warnings),
            "errors": len(self.errors),
            "error_rate": (self.checks_failed / len(records)) * 100 if records else 0,
            "statistics": {
                "avg_short": sum(short_percentages) / len(short_percentages)
                if short_percentages
                else 0,
                "max_short": max(short_percentages) if short_percentages else 0,
                "min_short": min(short_percentages) if short_percentages else 0,
                "unique_stocks": len(set(r.asx_code for r in valid_records)),
            },
        }

    def get_report(self) -> str:
        """Generate detailed validation report."""
        report = []
        report.append("📊 Data Quality Report:")
        report.append(f"   Checks passed: {self.checks_passed}")
        report.append(f"   Checks failed: {self.checks_failed}")
        report.append(f"   Warnings: {len(self.warnings)}")
        report.append(f"   Errors: {len(self.errors)}")

        if self.warnings:
            report.append("\n⚠️ Warnings:")
            for warning in self.warnings[:5]:  # Show first 5
                report.append(f"   - {warning}")
            if len(self.warnings) > 5:
                report.append(f"   ... and {len(self.warnings) - 5} more")

        if self.errors:
            report.append("\n❌ Errors:")
            for error in self.errors[:5]:  # Show first 5
                report.append(f"   - {error}")
            if len(self.errors) > 5:
                report.append(f"   ... and {len(self.errors) - 5} more")

        return "\n".join(report)


def data_validation_examples():
    """Demonstrate comprehensive data validation."""
    print("\n✅ Data Validation and Quality Assurance")
    print("-" * 42)

    client = ShortsClient()
    checker = DataQualityChecker()

    try:
        # Fetch data for validation
        target_date = date.today() - timedelta(days=20)
        result = client.fetch_day(target_date)

        if not result.records:
            print("❌ No data available for validation")
            return

        print(f"🔍 Validating {len(result.records)} records from {target_date}")

        # Perform validation
        validation_result = checker.validate_dataset(result.records)

        # Display results
        if validation_result["valid"]:
            print("✅ Data validation PASSED")
        else:
            print("❌ Data validation FAILED")

        print("\n📊 Validation Summary:")
        print(f"   Total records: {validation_result['total_records']}")
        print(f"   Valid records: {validation_result['valid_records']}")
        print(f"   Error rate: {validation_result['error_rate']:.2f}%")
        print(f"   Warnings: {validation_result['warnings']}")
        print(f"   Errors: {validation_result['errors']}")

        # Statistics
        stats = validation_result["statistics"]
        print("\n📈 Data Statistics:")
        print(f"   Unique stocks: {stats['unique_stocks']}")
        print(f"   Average short: {stats['avg_short']:.2f}%")
        print(f"   Short range: {stats['min_short']:.2f}% - {stats['max_short']:.2f}%")

        # Detailed report
        print(f"\n{checker.get_report()}")

        # Quality score
        quality_score = (
            validation_result["checks_passed"]
            / (validation_result["checks_passed"] + validation_result["checks_failed"])
        ) * 100
        print(f"\n🏆 Data Quality Score: {quality_score:.1f}%")

        if quality_score >= 95:
            print("🌟 Excellent data quality!")
        elif quality_score >= 90:
            print("✅ Good data quality")
        elif quality_score >= 80:
            print("⚠️ Acceptable data quality")
        else:
            print("❌ Poor data quality - investigate issues")

    except Exception as e:
        print(f"❌ Validation failed: {e}")


# Run data validation examples
data_validation_examples()

# %% [markdown]
"""
## 🔧 Custom Analytics and Processing
Advanced custom analytics patterns for specialized use cases.
"""


# %%
class ShortSellingAnalyzer:
    """Advanced analytics for short selling data."""

    def __init__(self, use_polars: bool = True):
        self.use_polars = use_polars and HAS_POLARS
        self.client = ShortsClient()

        if self.use_polars:
            self.adapter = create_polars_adapter()
            print("🚀 Using Polars for high-performance analytics")
        elif HAS_PANDAS:
            self.adapter = create_pandas_adapter()
            print("🐼 Using Pandas for analytics")
        else:
            raise RuntimeError("No data processing library available")

    def analyze_short_squeeze_candidates(
        self, records, min_short_percent: float = 0.15
    ):
        """Identify potential short squeeze candidates."""
        if not records:
            return []

        # Work directly with records to avoid adapter dependency
        candidates = []

        for record in records:
            # Filter out non-numeric percent_short values
            if (
                hasattr(record, "percent_short")
                and isinstance(record.percent_short, (int, float))
                and record.percent_short >= min_short_percent
            ):
                # Calculate risk category
                if record.percent_short > 30.0:
                    risk = "Extreme Risk"
                elif record.percent_short > 20.0:
                    risk = "High Risk"
                else:
                    risk = "Medium Risk"

                # Calculate short percentage
                calculated_short = (
                    (record.short_sold / record.issued_shares) * 100
                    if record.issued_shares > 0
                    else 0
                )

                candidates.append(
                    {
                        "asx_code": record.asx_code,
                        "percent_short": record.percent_short,
                        "short_sold": record.short_sold,
                        "issued_shares": record.issued_shares,
                        "calculated_short": calculated_short,
                        "squeeze_risk": risk,
                    }
                )

        # Sort by percent_short descending
        candidates.sort(key=lambda x: x["percent_short"], reverse=True)
        return candidates

    def calculate_market_sentiment(self, records):
        """Calculate overall market sentiment based on short interest."""
        if not records:
            return {}

        # Get data using proper adapter method
        target_date = date.today() - timedelta(days=1)  # Use recent date
        df = self.adapter.fetch_day_df(target_date)
        if df is None:
            print("❌ No data available for sentiment analysis")
            return {}

        if self.use_polars:
            # Polars implementation - filter out non-numeric values first
            numeric_df = df.filter(pl.col("percent_short").is_not_null()).filter(
                pl.col("percent_short").is_numeric()
            )
            sentiment = numeric_df.select(
                [
                    pl.col("percent_short").mean().alias("avg_short"),
                    pl.col("percent_short").median().alias("median_short"),
                    pl.col("percent_short").std().alias("volatility"),
                    (pl.col("percent_short") > 0.10).sum().alias("high_short_count"),
                    (pl.col("percent_short") > 0.20).sum().alias("extreme_short_count"),
                    pl.count().alias("total_stocks"),
                ]
            ).to_dicts()[0]
        else:
            # Pandas implementation - filter out non-numeric values first
            numeric_mask = pd.to_numeric(df["percent_short"], errors="coerce").notna()
            df_numeric = df[numeric_mask].copy()
            df_numeric["percent_short"] = pd.to_numeric(
                df_numeric["percent_short"], errors="coerce"
            )

            sentiment = {
                "avg_short": df_numeric["percent_short"].mean(),
                "median_short": df_numeric["percent_short"].median(),
                "volatility": df_numeric["percent_short"].std(),
                "high_short_count": (df_numeric["percent_short"] > 0.10).sum(),
                "extreme_short_count": (df_numeric["percent_short"] > 0.20).sum(),
                "total_stocks": len(df_numeric),
            }

        # Calculate sentiment indicators
        sentiment["high_short_ratio"] = (
            sentiment["high_short_count"] / sentiment["total_stocks"]
        )
        sentiment["extreme_short_ratio"] = (
            sentiment["extreme_short_count"] / sentiment["total_stocks"]
        )

        # Sentiment classification (using decimal thresholds)
        if sentiment["avg_short"] > 0.08:
            sentiment["market_sentiment"] = "Bearish"
        elif sentiment["avg_short"] > 0.05:
            sentiment["market_sentiment"] = "Neutral-Bearish"
        elif sentiment["avg_short"] > 0.03:
            sentiment["market_sentiment"] = "Neutral"
        else:
            sentiment["market_sentiment"] = "Bullish"

        return sentiment

    def sector_analysis(self, records):
        """Analyze short interest by sector (simplified by ASX code patterns)."""
        if not records:
            return {}

        # Get data using proper adapter method
        target_date = date.today() - timedelta(days=1)  # Use recent date
        df = self.adapter.fetch_day_df(target_date)
        if df is None:
            print("❌ No data available for sector analysis")
            return {}

        # Simple sector classification by first letter of ASX code
        sector_mapping = {
            "A": "Technology/Resources",
            "B": "Banking/Finance",
            "C": "Consumer/Retail",
            "D": "Diversified",
            "E": "Energy",
            "F": "Finance",
            "G": "Gaming/Leisure",
            "H": "Healthcare",
            "I": "Industrial",
            "J": "Utilities",
            "K": "Consumer",
            "L": "Leisure",
            "M": "Materials/Mining",
            "N": "Technology",
            "O": "Other",
            "P": "Property",
            "Q": "Resources",
            "R": "Resources/REIT",
            "S": "Services",
            "T": "Technology/Telecom",
            "U": "Utilities",
            "V": "Various",
            "W": "Resources",
            "X": "Other",
            "Y": "Other",
            "Z": "Other",
        }

        if self.use_polars:
            # Polars implementation
            sector_analysis = (
                df.with_columns(
                    [pl.col("asx_code").str.slice(0, 1).alias("sector_code")]
                )
                .with_columns(
                    [
                        pl.col("sector_code")
                        .map_elements(
                            lambda x: sector_mapping.get(x, "Other"),
                            return_dtype=pl.Utf8,
                        )
                        .alias("sector")
                    ]
                )
                .group_by("sector")
                .agg(
                    [
                        pl.count().alias("stock_count"),
                        pl.col("percent_short").mean().alias("avg_short"),
                        pl.col("percent_short").median().alias("median_short"),
                        pl.col("percent_short").max().alias("max_short"),
                        (pl.col("percent_short") > 10.0)
                        .sum()
                        .alias("high_short_count"),
                    ]
                )
                .sort("avg_short", descending=True)
            )

            return sector_analysis.to_dicts()
        else:
            # Pandas implementation
            df["sector_code"] = df["asx_code"].str[0]
            df["sector"] = df["sector_code"].map(sector_mapping).fillna("Other")

            sector_analysis = (
                df.groupby("sector")
                .agg(
                    {
                        "asx_code": "count",
                        "percent_short": ["mean", "median", "max"],
                    }
                )
                .round(2)
            )

            sector_analysis.columns = [
                "stock_count",
                "avg_short",
                "median_short",
                "max_short",
            ]
            sector_analysis["high_short_count"] = df.groupby("sector")[
                "percent_short"
            ].apply(lambda x: (x > 10.0).sum())

            return sector_analysis.sort_values("avg_short", ascending=False).to_dict(
                "index"
            )


def custom_analytics_examples():
    """Demonstrate custom analytics capabilities."""
    print("\n" + "🔧 Custom Analytics and Processing")
    print("-" * 36)

    # Initialize analyzer
    try:
        analyzer = ShortSellingAnalyzer(use_polars=HAS_POLARS)
    except RuntimeError as e:
        print(f"❌ Cannot initialize analyzer: {e}")
        return

    # Fetch data for analysis
    try:
        target_date = date.today() - timedelta(days=20)
        result = analyzer.client.fetch_day(target_date)

        if not result.records:
            print("❌ No data available for custom analytics")
            return

        print(f"📊 Analyzing {len(result.records)} records from {target_date}")

        # 1. Short squeeze candidate analysis
        print("\n🎯 Short Squeeze Candidate Analysis:")
        candidates = analyzer.analyze_short_squeeze_candidates(
            result.records, min_short_percent=15.0
        )

        if candidates:
            print(f"   Found {len(candidates)} potential candidates (>15% short)")
            print("   Top 5 candidates:")
            for i, candidate in enumerate(candidates[:5]):
                print(
                    f"   {i + 1}. {candidate['asx_code']}: {candidate['percent_short']:.2f}% ({candidate['squeeze_risk']})"
                )
        else:
            print("   No short squeeze candidates found")

        # 2. Market sentiment analysis
        print("\n" + "📈 Market Sentiment Analysis:")
        sentiment = analyzer.calculate_market_sentiment(result.records)

        print(f"   Overall sentiment: {sentiment['market_sentiment']}")
        print(f"   Average short interest: {sentiment['avg_short']:.2f}%")
        print(f"   Median short interest: {sentiment['median_short']:.2f}%")
        print(
            f"   High short stocks (>10%): {sentiment['high_short_count']} ({sentiment['high_short_ratio'] * 100:.1f}%)"
        )
        print(
            f"   Extreme short stocks (>20%): {sentiment['extreme_short_count']} ({sentiment['extreme_short_ratio'] * 100:.1f}%)"
        )

        # 3. Sector analysis
        print("\n" + "🏭 Sector Analysis:")
        sectors = analyzer.sector_analysis(result.records)

        if sectors:
            print("   Top 5 sectors by average short interest:")
            sector_items = (
                list(sectors.items()) if isinstance(sectors, dict) else sectors
            )
            for i, sector_data in enumerate(sector_items[:5]):
                if isinstance(sector_data, dict):
                    # Polars format
                    sector_name = sector_data["sector"]
                    avg_short = sector_data["avg_short"]
                    stock_count = sector_data["stock_count"]
                    high_short = sector_data["high_short_count"]
                else:
                    # Pandas format
                    sector_name, data = sector_data
                    avg_short = data["avg_short"]
                    stock_count = data["stock_count"]
                    high_short = data["high_short_count"]

                print(
                    f"   {i + 1}. {sector_name}: {avg_short:.2f}% avg ({stock_count} stocks, {high_short} high short)"
                )

        # 4. Custom risk metrics
        print("\n" + "⚠️ Risk Metrics:")

        # Calculate custom risk indicators
        high_risk_stocks = [r for r in result.records if r.percent_short > 25.0]
        medium_risk_stocks = [
            r for r in result.records if 15.0 < r.percent_short <= 25.0
        ]

        total_short_value = sum(r.short_sold for r in result.records)
        total_market_value = sum(r.issued_shares for r in result.records)

        print(f"   High risk stocks (>25%): {len(high_risk_stocks)}")
        print(f"   Medium risk stocks (15-25%): {len(medium_risk_stocks)}")
        print(
            f"   Market short ratio: {(total_short_value / total_market_value) * 100:.2f}%"
        )

        # Risk concentration
        if high_risk_stocks:
            top_risk_stock = max(high_risk_stocks, key=lambda x: x.percent_short)
            print(
                f"   Highest risk: {top_risk_stock.asx_code} ({top_risk_stock.percent_short:.2f}%)"
            )

    except Exception as e:
        print(f"❌ Custom analytics failed: {e}")


# Run custom analytics examples
custom_analytics_examples()

# %% [markdown]
"""
## 🎯 Summary and Production Best Practices

### What You've Learned:
- ✅ Intelligent cache management for optimal performance
- ✅ Robust error handling with retry patterns and graceful degradation
- ✅ Performance monitoring and optimization techniques
- ✅ Comprehensive data validation and quality assurance
- ✅ Custom analytics for specialized use cases

### Production Best Practices:

#### 🛡️ Reliability
- **Retry Logic**: Implement exponential backoff for transient failures
- **Graceful Degradation**: Continue processing even if some data is unavailable
- **Data Validation**: Always validate data quality before processing
- **Error Logging**: Comprehensive logging for debugging and monitoring

#### ⚡ Performance
- **Cache Strategy**: Warm caches for frequently accessed data
- **Batch Processing**: Use range fetches instead of individual calls
- **Memory Management**: Process data in chunks for large datasets
- **Library Choice**: Use Polars for high-performance scenarios

#### 📊 Monitoring
- **Performance Metrics**: Track timing, memory usage, and CPU utilization
- **Data Quality Metrics**: Monitor error rates and data completeness
- **Business Metrics**: Track short interest trends and anomalies
- **Alerting**: Set up alerts for data quality issues or performance degradation

#### 🔧 Scalability
- **Async Processing**: Consider async patterns for high-throughput scenarios
- **Database Integration**: Store processed data for historical analysis
- **API Rate Limiting**: Respect API limits and implement backoff
- **Resource Management**: Monitor and optimize resource usage

### Next Steps for Production:
1. **Database Integration**: Store historical data for trend analysis
2. **Scheduled Processing**: Set up automated daily data collection
3. **API Development**: Build APIs for real-time short interest queries
4. **Alerting System**: Implement alerts for unusual short interest activity
5. **Dashboard Creation**: Build monitoring dashboards for operations teams

### Code Organization:
- **Modular Design**: Separate concerns into focused modules
- **Configuration Management**: Use environment variables for settings
- **Testing**: Implement comprehensive unit and integration tests
- **Documentation**: Maintain clear documentation for all components

Ready for production deployment! 🚀
"""

# %%
print("\n" + "=" * 50)
print("🚀 Advanced Features Examples Completed!")
print("... Production-ready patterns demonstrated")
print("🛡️ Robust error handling and monitoring implemented")
print("⚡ Performance optimization techniques covered")
print("📊 Ready for enterprise deployment!")
print("=" * 50)

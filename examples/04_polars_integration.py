# %% [markdown]
"""
# ⚡ ASX Shorts Package - Polars Integration

This script demonstrates high-performance data processing with the `asxshorts` package using Polars:

- ⚡ **Lightning Fast**: Polars is built in Rust for maximum performance
- 🧠 **Lazy Evaluation**: Optimize query plans before execution
- 🔍 **Advanced Filtering**: Complex filtering with minimal memory usage
- 📊 **Aggregations**: High-speed grouping and statistical operations
- 📈 **Time Series**: Efficient time-based analysis
- 🏁 **Performance**: Compare Polars vs Pandas speed

## Prerequisites
```bash
pip install 'asxshorts[polars]' polars
```

## Why Polars?
- **Speed**: 10-100x faster than pandas for many operations
- **Memory Efficiency**: Lower memory usage with lazy evaluation
- **Parallel Processing**: Automatic parallelization
- **Type Safety**: Strong typing system
"""

# %% [markdown]
"""
## 📦 Setup and Imports
Import required modules and check for Polars availability.
"""

# %%
import time
from datetime import date, timedelta

from asxshorts import ShortsClient, create_polars_adapter
from asxshorts.errors import FetchError, NotFoundError

# Check for polars availability
try:
    import polars as pl

    HAS_POLARS = True
    print("✅ Polars available")
    print(f"   Version: {pl.__version__}")
except ImportError:
    HAS_POLARS = False
    print("⚡ Install polars for this example: pip install polars")

# Optional: Check for pandas for comparison
try:
    import pandas as pd

    HAS_PANDAS = True
    print("✅ Pandas available for comparison")
except ImportError:
    HAS_PANDAS = False
    print("🐼 Pandas not available for comparison")

if not HAS_POLARS:
    print("❌ This example requires Polars. Install with: pip install polars")
    exit(1)

# Initialize client and adapter
client = ShortsClient()
adapter = create_polars_adapter()
print("⚡ Polars Integration Examples - ASX Short Selling")
print("=" * 50)

# %% [markdown]
"""
## ⚡ Basic Polars Operations
Convert ASX shorts data to Polars DataFrame and explore basic operations.
"""


# %%
def basic_polars_operations() -> pl.DataFrame | None:
    """Demonstrate basic Polars DataFrame operations with ASX shorts data."""
    print("\n⚡ Basic Polars DataFrame Operations")
    print("-" * 40)

    # Fetch recent data
    target_date = date.today() - timedelta(days=20)

    try:
        # Fetch data directly as Polars DataFrame
        df = adapter.fetch_day_df(target_date)

        if df is None or df.is_empty():
            print(f"❌ No data available for {target_date}")
            return None

        print(f"✅ Loaded {len(df)} records into Polars DataFrame")
        print("\nDataFrame Info:")
        print(f"   Shape: {df.shape}")
        print(f"   Columns: {df.columns}")
        print(f"   Schema: {df.schema}")

        # Display basic statistics
        print("\n📊 Basic Statistics:")
        print(df.describe())

        # Show first few rows
        print("\n👀 First 5 rows:")
        print(df.head())

        # Data types and null counts
        print("\n🔍 Data Types and Null Counts:")
        print(df.null_count())

        return df

    except (NotFoundError, FetchError) as e:
        print(f"❌ Error: {e}")
        return None


# Run basic operations
df = basic_polars_operations()

# %% [markdown]
"""
## 🚀 High-Performance Filtering
Demonstrate Polars' efficient filtering capabilities.
"""


# %%
def high_performance_filtering(df: pl.DataFrame) -> None:
    """Demonstrate high-performance filtering with Polars."""
    if df is None or df.is_empty():
        print("❌ No DataFrame available for filtering")
        return

    print("\n🚀 High-Performance Filtering")
    print("-" * 32)

    # Filter out non-numeric percent_short values first
    numeric_df = (
        df.filter(pl.col("percent_short").is_not_null())
        .with_columns(pl.col("percent_short").cast(pl.String))  # Cast to string first
        .filter(pl.col("percent_short") != "-")  # Now we can safely compare strings
        .with_columns(
            pl.col("percent_short").cast(pl.Float64, strict=False)
        )  # Then cast to float
        .filter(pl.col("percent_short").is_not_null())  # Filter out failed conversions
    )

    print(f"📊 Working with {len(numeric_df)} records with valid percent_short data")

    # Basic filtering with expressions (0.10 = 10%)
    high_short = numeric_df.filter(pl.col("percent_short") > 0.10)
    print(f"📈 Stocks with >10% short interest: {len(high_short)}")

    # Complex filtering with multiple conditions (0.20 = 20%)
    extreme_short = numeric_df.filter(
        (pl.col("percent_short") > 0.20) & (pl.col("issued_shares") > 1_000_000)
    )
    print(f"🚨 High-volume stocks with >20% short: {len(extreme_short)}")

    # String operations
    tech_stocks = numeric_df.filter(pl.col("asx_code").str.starts_with("A"))
    print(f"🔤 Stocks starting with 'A': {len(tech_stocks)}")

    # Top N selection
    top_10_short = numeric_df.top_k(10, by="percent_short")
    print("\n🔥 Top 10 Most Shorted Stocks:")
    for row in top_10_short.iter_rows(named=True):
        print(f"   {row['asx_code']}: {row['percent_short'] * 100:.2f}%")

    # Quantile-based filtering
    q75 = numeric_df.select(pl.col("percent_short").quantile(0.75)).item()
    top_quartile = numeric_df.filter(pl.col("percent_short") > q75)
    print(f"\n📊 Top quartile (>{q75 * 100:.2f}%): {len(top_quartile)} stocks")

    # Conditional expressions (using decimal thresholds)
    df_with_category = numeric_df.with_columns(
        [
            pl.when(pl.col("percent_short") > 0.20)
            .then(pl.lit("Extreme"))
            .when(pl.col("percent_short") > 0.10)
            .then(pl.lit("High"))
            .when(pl.col("percent_short") > 0.05)
            .then(pl.lit("Medium"))
            .otherwise(pl.lit("Low"))
            .alias("short_category")
        ]
    )

    category_counts = df_with_category.group_by("short_category").count()
    print("\n🏷️ Short Interest Categories:")
    for row in category_counts.iter_rows(named=True):
        print(f"   {row['short_category']}: {row['count']} stocks")


# Run filtering examples
if df is not None:
    high_performance_filtering(df)

# %% [markdown]
"""
## 🧠 Lazy Evaluation
Demonstrate Polars' lazy evaluation for query optimization.
"""


# %%
def lazy_evaluation_example() -> pl.LazyFrame | None:
    """Demonstrate lazy evaluation with complex query optimization."""
    print("\n🧠 Lazy Evaluation Example")
    print("-" * 27)

    # Fetch data for multiple days
    end_date = date.today() - timedelta(days=20)
    start_date = end_date - timedelta(days=10)

    try:
        # Fetch range data directly as Polars DataFrame
        combined_df = adapter.fetch_range_df(start_date, end_date)

        if combined_df is None or combined_df.is_empty():
            print(f"❌ No data available for range {start_date} to {end_date}")
            return None

        # Convert report_date column to proper format and count unique days
        combined_df = combined_df.with_columns(
            pl.col("report_date").alias(
                "date"
            )  # Alias report_date as date for consistency
        )
        unique_days = combined_df.select("date").n_unique()
        print(f"✅ Combined {len(combined_df)} records across {unique_days} days")

        # Create lazy frame for complex operations
        lazy_df = combined_df.lazy()

        # Build complex query with lazy evaluation
        complex_query = (
            lazy_df.filter(pl.col("percent_short").is_not_null())
            .with_columns(
                pl.col("percent_short").cast(pl.String)
            )  # Cast to string first
            .filter(pl.col("percent_short") != "-")  # Filter out non-numeric values
            .with_columns(
                pl.col("percent_short").cast(pl.Float64, strict=False)
            )  # Cast to float
            .filter(
                pl.col("percent_short").is_not_null()
            )  # Filter out failed conversions
            .filter(pl.col("percent_short") > 5.0)  # Filter early
            .with_columns(
                [
                    pl.col("date").alias(
                        "date_parsed"
                    ),  # date is already a proper date type
                    (pl.col("percent_short") * pl.col("issued_shares") / 100).alias(
                        "short_value"
                    ),
                ]
            )
            .group_by(["date_parsed", "asx_code"])
            .agg(
                [
                    pl.col("percent_short").mean().alias("avg_short"),
                    pl.col("short_value").sum().alias("total_short_value"),
                    pl.len().alias("records"),
                ]
            )
            .filter(pl.col("avg_short") > 10.0)
            .sort(["date_parsed", "avg_short"], descending=[False, True])
        )

        print("\n🔍 Query Plan:")
        print(complex_query.explain())

        # Execute the lazy query
        print("\n⚡ Executing optimized query...")
        start_time = time.time()
        result = complex_query.collect()
        execution_time = time.time() - start_time

        print(f"✅ Query executed in {execution_time:.3f} seconds")
        print(f"📊 Result shape: {result.shape}")

        if not result.is_empty():
            print("\n🎯 Top results:")
            print(result.head(10))

        return lazy_df

    except (NotFoundError, FetchError) as e:
        print(f"❌ Error in lazy evaluation: {e}")
        return None


# Run lazy evaluation example
lazy_df = lazy_evaluation_example()

# %% [markdown]
"""
## 📈 Time Series Analysis
Efficient time-based analysis with Polars.
"""


# %%
def time_series_analysis_polars(df: pl.DataFrame) -> None:
    """Demonstrate time series analysis with Polars."""
    if df is None or df.is_empty():
        print("❌ No DataFrame available for time series analysis")
        return

    print("\n📈 Time Series Analysis with Polars")
    print("-" * 37)

    # Check if we have report_date column
    if "report_date" not in df.columns:
        print("❌ No report_date column available for time series analysis")
        return

    # Ensure report_date is properly parsed (data cleaning is now handled by adapter)
    df_ts = df.with_columns([pl.col("report_date").alias("date_parsed")]).filter(
        pl.col("percent_short").is_not_null()
    )  # Remove null values

    # Daily aggregations
    daily_stats = (
        df_ts.group_by("date_parsed")
        .agg(
            [
                pl.col("percent_short").mean().alias("avg_short"),
                pl.col("percent_short").median().alias("median_short"),
                pl.col("percent_short").max().alias("max_short"),
                pl.col("percent_short").min().alias("min_short"),
                pl.col("percent_short").std().alias("std_short"),
                pl.len().alias("stock_count"),
            ]
        )
        .sort("date_parsed")
    )

    print("📊 Daily Statistics:")
    print(daily_stats)

    # Rolling statistics
    if len(daily_stats) >= 3:
        rolling_stats = daily_stats.with_columns(
            [
                pl.col("avg_short").rolling_mean(window_size=3).alias("rolling_avg_3d"),
                pl.col("avg_short").rolling_std(window_size=3).alias("rolling_std_3d"),
            ]
        )

        print("\n📈 Rolling Statistics (3-day window):")
        print(
            rolling_stats.select(
                ["date_parsed", "avg_short", "rolling_avg_3d", "rolling_std_3d"]
            )
        )

    # Stock consistency analysis
    stock_consistency = (
        df_ts.group_by("asx_code")
        .agg(
            [
                pl.col("percent_short").mean().alias("avg_short"),
                pl.col("percent_short").std().alias("std_short"),
                pl.col("date_parsed").n_unique().alias("days_present"),
                pl.col("percent_short").max().alias("max_short"),
            ]
        )
        .filter(pl.col("days_present") >= 3)  # Stocks present on 3+ days
        .filter(pl.col("avg_short") > 15.0)  # High average short interest
        .sort("avg_short", descending=True)
    )

    if not stock_consistency.is_empty():
        print("\n🎯 Consistently High Short Interest (>15%, 3+ days):")
        for row in stock_consistency.head(10).iter_rows(named=True):
            print(
                f"   {row['asx_code']}: {row['avg_short']:.2f}% avg "
                f"({row['days_present']} days, max: {row['max_short']:.2f}%)"
            )

    # Trend analysis
    if len(daily_stats) >= 2:
        first_day = daily_stats.select("avg_short").item(0, 0)
        last_day = daily_stats.select("avg_short").item(-1, 0)
        trend_change = last_day - first_day

        print("\n📈 Trend Analysis:")
        print(f"   First day average: {first_day:.2f}%")
        print(f"   Last day average: {last_day:.2f}%")
        print(f"   Change: {trend_change:+.2f}%")
        print(
            f"   Direction: {'📈 Increasing' if trend_change > 0 else '📉 Decreasing'}"
        )


# Run time series analysis
if df is not None and "report_date" in df.columns:
    time_series_analysis_polars(df)

# %% [markdown]
"""
## 🏁 Performance Comparison
Compare Polars vs Pandas performance on identical operations.
"""


# %%
def performance_comparison() -> None:
    """Compare Polars vs Pandas performance."""
    if not HAS_PANDAS:
        print("❌ Pandas not available for comparison")
        return

    print("\n🏁 Performance Comparison: Polars vs Pandas")
    print("-" * 47)

    # Get data for comparison
    target_date = date.today() - timedelta(days=20)

    try:
        # Create both adapters
        polars_adapter = create_polars_adapter()

        # Import pandas adapter
        from asxshorts import create_pandas_adapter

        pandas_adapter = create_pandas_adapter()

        # Test 1: DataFrame creation
        print("\n🔄 Test 1: DataFrame Creation")

        start_time = time.time()
        polars_df = polars_adapter.fetch_day_df(target_date)
        polars_creation_time = time.time() - start_time

        start_time = time.time()
        pandas_df = pandas_adapter.fetch_day_df(target_date)
        pandas_creation_time = time.time() - start_time

        if polars_df is None or pandas_df is None:
            print("❌ No data available for performance comparison")
            return

        print(f"📊 Testing with {len(polars_df)} records")

        print(f"   Polars: {polars_creation_time:.4f}s")
        print(f"   Pandas: {pandas_creation_time:.4f}s")
        print(f"   Speedup: {pandas_creation_time / polars_creation_time:.1f}x")

        # Test 2: Filtering
        print("\n🔍 Test 2: Filtering (>10% short)")

        start_time = time.time()
        # Filter non-numeric values and apply threshold (0.10 = 10%)
        polars_filtered = (
            polars_df.filter(pl.col("percent_short").is_not_null())
            .with_columns(
                pl.col("percent_short").cast(pl.String)
            )  # Cast to string first
            .filter(pl.col("percent_short") != "-")  # Filter out non-numeric values
            .with_columns(
                pl.col("percent_short").cast(pl.Float64, strict=False)
            )  # Cast to float
            .filter(
                pl.col("percent_short").is_not_null()
            )  # Filter out failed conversions
            .filter(pl.col("percent_short") > 0.10)  # Apply threshold
        )
        polars_filter_time = time.time() - start_time

        start_time = time.time()
        # Filter non-numeric values and apply threshold (0.10 = 10%)
        numeric_mask = (pandas_df["percent_short"] != "-") & pandas_df[
            "percent_short"
        ].notna()
        pandas_filtered = pandas_df[
            numeric_mask
            & (pd.to_numeric(pandas_df["percent_short"], errors="coerce") > 0.10)
        ]
        pandas_filter_time = time.time() - start_time

        print(f"   Polars: {polars_filter_time:.4f}s ({len(polars_filtered)} results)")
        print(f"   Pandas: {pandas_filter_time:.4f}s ({len(pandas_filtered)} results)")
        print(f"   Speedup: {pandas_filter_time / polars_filter_time:.1f}x")

        # Test 3: Aggregation
        print("\n📊 Test 3: Aggregation (mean, max, count)")

        # Data cleaning is now handled by adapter
        start_time = time.time()
        polars_agg = polars_df.select(
            [
                pl.col("percent_short").mean().alias("mean_short"),
                pl.col("percent_short").max().alias("max_short"),
                pl.len().alias("count"),
            ]
        )
        polars_agg_time = time.time() - start_time

        start_time = time.time()
        pandas_agg = pandas_df.agg({"percent_short": ["mean", "max", "count"]})
        pandas_agg_time = time.time() - start_time

        print(f"   Polars: {polars_agg_time:.4f}s")
        print(f"   Pandas: {pandas_agg_time:.4f}s")
        print(f"   Speedup: {pandas_agg_time / polars_agg_time:.1f}x")

        # Test 4: Sorting
        print("\n🔄 Test 4: Sorting by percent_short")

        start_time = time.time()
        polars_sorted = polars_df.sort("percent_short", descending=True)
        polars_sort_time = time.time() - start_time

        start_time = time.time()
        pandas_sorted = pandas_df.sort_values("percent_short", ascending=False)
        pandas_sort_time = time.time() - start_time

        print(f"   Polars: {polars_sort_time:.4f}s")
        print(f"   Pandas: {pandas_sort_time:.4f}s")
        print(f"   Speedup: {pandas_sort_time / polars_sort_time:.1f}x")

        # Overall comparison
        total_polars = (
            polars_creation_time
            + polars_filter_time
            + polars_agg_time
            + polars_sort_time
        )
        total_pandas = (
            pandas_creation_time
            + pandas_filter_time
            + pandas_agg_time
            + pandas_sort_time
        )

        print("\n🏆 Overall Performance:")
        print(f"   Total Polars time: {total_polars:.4f}s")
        print(f"   Total Pandas time: {total_pandas:.4f}s")
        print(f"   Overall speedup: {total_pandas / total_polars:.1f}x")

        # Memory usage comparison
        print("\n💾 Memory Usage:")
        print(f"   Polars DataFrame: {polars_df.estimated_size('mb'):.2f} MB")
        print(
            f"   Pandas DataFrame: {pandas_df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
        )

    except Exception as e:
        print(f"❌ Error in performance comparison: {e}")


# Run performance comparison
performance_comparison()

# %% [markdown]
"""
## 💾 Data Export with Polars
Demonstrate efficient data export capabilities.
"""


# %%
def export_polars_data(df: pl.DataFrame) -> None:
    """Demonstrate data export capabilities with Polars."""
    if df is None or df.is_empty():
        print("❌ No DataFrame available for export")
        return

    print("\n💾 Polars Data Export Examples")
    print("-" * 31)

    # Prepare sample data
    export_df = df.head(100)

    try:
        # CSV export - exclude nested/struct columns that CSV doesn't support
        csv_columns = [
            col
            for col, dtype in export_df.schema.items()
            if not isinstance(dtype, pl.Struct)
        ]
        csv_df = export_df.select(csv_columns)

        csv_file = "polars_asx_shorts.csv"
        csv_df.write_csv(csv_file)
        print(f"✅ Exported to CSV: {csv_file} ({len(csv_columns)} columns)")

        # Parquet export (efficient columnar format) - exclude empty structs
        parquet_columns = [
            col
            for col, dtype in export_df.schema.items()
            if not (isinstance(dtype, pl.Struct) and len(dtype.fields) == 0)
        ]
        parquet_df = export_df.select(parquet_columns)

        parquet_file = "polars_asx_shorts.parquet"
        parquet_df.write_parquet(parquet_file)
        print(
            f"✅ Exported to Parquet: {parquet_file} ({len(parquet_columns)} columns)"
        )

        # JSON export - supports nested data
        json_file = "polars_asx_shorts.json"
        export_df.write_json(json_file)
        print(
            f"✅ Exported to JSON: {json_file} (all {len(export_df.columns)} columns)"
        )

        # Filtered export - exclude struct columns for CSV
        high_short = (
            export_df.filter(pl.col("percent_short").is_not_null())
            .filter(
                pl.col("percent_short") > 10.0
            )  # Apply threshold (data is already clean)
            .select(csv_columns)  # Use same CSV-compatible columns
        )
        if not high_short.is_empty():
            high_short_file = "polars_high_short.csv"
            high_short.write_csv(high_short_file)
            print(
                f"✅ Exported high short interest: {high_short_file} ({len(high_short)} records)"
            )

        print("\n📊 Export Summary:")
        print(f"   Total records: {len(export_df)}")
        print(
            f"   High short records: {len(high_short) if not high_short.is_empty() else 0}"
        )

    except Exception as e:
        print(f"❌ Export error: {e}")


# Run export examples
if df is not None:
    export_polars_data(df)

# %% [markdown]
"""
## 🎯 Summary and Best Practices

### What You've Learned:
- ✅ Converting ASX shorts data to Polars DataFrames
- ✅ High-performance filtering and operations
- ✅ Lazy evaluation for query optimization
- ✅ Efficient time series analysis
- ✅ Performance comparison with Pandas
- ✅ Fast data export in multiple formats

### Polars Best Practices:
- **Lazy Evaluation**: Use `.lazy()` for complex queries
- **Early Filtering**: Filter data as early as possible in the pipeline
- **Column Selection**: Select only needed columns to reduce memory
- **Parallel Processing**: Polars automatically parallelizes operations
- **Type Safety**: Leverage Polars' strong typing system

### Performance Tips:
- Use Parquet format for large datasets
- Leverage lazy evaluation for complex transformations
- Use expressions (`pl.col()`) instead of string column names
- Consider streaming for very large datasets
- Use `scan_*` functions for lazy file reading

### When to Use Polars:
- **Large Datasets**: >1M rows where performance matters
- **Complex Queries**: Multiple filtering and aggregation steps
- **Memory Constraints**: When pandas uses too much memory
- **Production Systems**: Where speed and reliability are critical

### Next Steps:
- 🚀 **Advanced Features**: Explore `05_advanced_features.py` for production patterns
- 📊 **Custom Analysis**: Build high-performance analysis pipelines
- 🔄 **Streaming**: Try Polars streaming for massive datasets

Lightning fast data processing! ⚡
"""

# %%
print("\n" + "=" * 50)
print("⚡ Polars Integration Examples Completed!")
print("... High-performance data processing demonstrated")
print("🚀 Ready for production-scale analysis with advanced features")

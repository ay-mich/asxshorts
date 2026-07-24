# %% [markdown]
"""
# 🐼 ASX Shorts Package - Pandas Integration

This script demonstrates powerful pandas integration with the `asxshorts` package:

- 📊 **DataFrame Operations**: Convert short selling data to pandas DataFrames
- 🔍 **Filtering & Analysis**: Advanced data filtering and statistical analysis
- 📈 **Time Series Analysis**: Analyze trends over time with pandas
- 🚀 **Advanced Operations**: Grouping, pivoting, and complex transformations
- 💾 **Data Export**: Save results in various formats (CSV, Excel, JSON)
- 📊 **Visualization**: Create charts directly from DataFrames

## Prerequisites
```bash
pip install 'asxshorts[pandas]' matplotlib seaborn openpyxl
```

## Why Pandas?
- **Familiar**: Most popular data analysis library in Python
- **Rich Ecosystem**: Extensive visualization and analysis tools
- **Excel Integration**: Easy export to Excel with formatting
- **Mature**: Well-documented with extensive community support
"""

# %% [markdown]
"""
## 📦 Setup and Imports
Import required modules and check for pandas availability.
"""

# %%
from datetime import date, timedelta

from asxshorts import ShortsClient, create_pandas_adapter
from asxshorts.errors import FetchError, NotFoundError

# Check for pandas availability
try:
    import pandas as pd

    HAS_PANDAS = True
    print("✅ Pandas available")
except ImportError:
    HAS_PANDAS = False
    print("🐼 Install pandas for this example: pip install pandas")

# Optional visualization imports
try:
    import matplotlib.pyplot as plt
    import seaborn as sns

    HAS_PLOTTING = True
    print("✅ Plotting libraries available")
except ImportError:
    HAS_PLOTTING = False
    print("📊 Install matplotlib/seaborn for plotting: pip install matplotlib seaborn")

if not HAS_PANDAS:
    print("❌ This example requires pandas. Install with: pip install pandas")
    exit(1)

# Initialize client and adapter
client = ShortsClient()
adapter = create_pandas_adapter()
print("🚀 Pandas Integration Examples - ASX Short Selling")
print("=" * 50)

# %% [markdown]
"""
## 🐼 Basic DataFrame Operations
Convert ASX shorts data to pandas DataFrame and explore basic operations.
"""


# %%
def basic_dataframe_operations() -> pd.DataFrame | None:
    """Demonstrate basic DataFrame operations with ASX shorts data."""
    print("\n🐼 Basic Pandas DataFrame Operations")
    print("-" * 40)

    # Fetch recent data
    target_date = date.today() - timedelta(days=20)

    try:
        # Use PandasAdapter to fetch data directly as DataFrame
        df = adapter.fetch_day_df(target_date)

        if df is None or df.empty:
            print(f"❌ No data available for {target_date}")
            return None

        print(f"✅ Loaded {len(df)} records into DataFrame")
        print("\nDataFrame Info:")
        print(f"   Shape: {df.shape}")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Memory usage: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")

        # Display basic statistics
        print("\n📊 Basic Statistics:")
        print(df.describe())

        # Show first few rows
        print("\n👀 First 5 rows:")
        print(df.head())

        # Data types
        print("\n🔍 Data Types:")
        print(df.dtypes)

        return df

    except (NotFoundError, FetchError) as e:
        print(f"❌ Error: {e}")
        return None


# Run basic operations
df = basic_dataframe_operations()

# %% [markdown]
"""
## 🔍 Filtering and Analysis
Demonstrate advanced filtering and statistical analysis with pandas.
"""


# %%
def filtering_and_analysis(df: pd.DataFrame) -> None:
    """Demonstrate filtering and analysis operations."""
    if df is None or df.empty:
        print("❌ No DataFrame available for analysis")
        return

    print("\n🔍 Filtering and Analysis")
    print("-" * 30)

    # Filter out non-numeric percent_short values (e.g., '-' strings)
    numeric_df = df[pd.to_numeric(df["percent_short"], errors="coerce").notna()].copy()
    filtered_count = len(df) - len(numeric_df)
    if filtered_count > 0:
        print(
            f"⚠️  Filtered out {filtered_count} records with non-numeric percent_short values"
        )

    # Basic filtering (using decimal thresholds: 0.10 = 10%)
    high_short = numeric_df[numeric_df["percent_short"] > 0.10]
    print(f"📈 Stocks with >10% short interest: {len(high_short)}")

    # Multiple conditions
    extreme_short = numeric_df[
        (numeric_df["percent_short"] > 0.20) & (numeric_df["issued_shares"] > 1000000)
    ]
    print(f"🚨 High-volume stocks with >20% short: {len(extreme_short)}")

    # Top performers
    top_10_short = numeric_df.nlargest(10, "percent_short")
    print("\n🔥 Top 10 Most Shorted Stocks:")
    for idx, row in top_10_short.iterrows():
        print(
            f"   {row['asx_code']}: {row['percent_short'] * 100:.2f}%"
        )  # Convert to percentage for display

    # Statistical analysis by ranges (using decimal bins)
    print("\n📊 Short Interest Distribution:")
    bins = [0, 0.05, 0.10, 0.15, 0.20, float("inf")]  # Decimal format
    labels = ["0-5%", "5-10%", "10-15%", "15-20%", "20%+"]
    numeric_df["short_range"] = pd.cut(
        numeric_df["percent_short"], bins=bins, labels=labels, right=False
    )

    distribution = numeric_df["short_range"].value_counts().sort_index()
    for range_label, count in distribution.items():
        percentage = (count / len(numeric_df)) * 100
        print(f"   {range_label}: {count} stocks ({percentage:.1f}%)")

    # Correlation analysis
    numeric_cols = numeric_df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 1:
        print("\n🔗 Correlation Matrix:")
        corr_matrix = numeric_df[numeric_cols].corr()
        print(corr_matrix.round(3))


# Run filtering and analysis
if df is not None:
    filtering_and_analysis(df)

# %% [markdown]
"""
## 📈 Time Series Analysis
Analyze short selling trends over time using pandas time series capabilities.
"""


# %%
def time_series_analysis() -> pd.DataFrame | None:
    """Demonstrate time series analysis with pandas."""
    print("\n📈 Time Series Analysis")
    print("-" * 25)

    # Fetch data for multiple days
    end_date = date.today() - timedelta(days=20)
    start_date = end_date - timedelta(days=10)

    try:
        # Use PandasAdapter to fetch range data directly as DataFrame
        combined_df = adapter.fetch_range_df(start_date, end_date)

        if combined_df is None or combined_df.empty:
            print(f"❌ No data available for range {start_date} to {end_date}")
            return None

        # The DataFrame already has 'report_date' column, rename it to 'date' for consistency
        combined_df = combined_df.rename(columns={"report_date": "date"})
        combined_df["date"] = pd.to_datetime(combined_df["date"])

        # Count unique days in the data
        unique_days = combined_df["date"].nunique()
        print(f"✅ Combined {len(combined_df)} records across {unique_days} days")

        # Time series aggregations
        daily_stats = (
            combined_df.groupby("date")
            .agg(
                {
                    "percent_short": ["mean", "median", "max", "min", "std"],
                    "asx_code": "count",
                }
            )
            .round(2)
        )

        # Flatten column names
        daily_stats.columns = ["_".join(col).strip() for col in daily_stats.columns]
        daily_stats = daily_stats.rename(columns={"asx_code_count": "total_stocks"})

        print("\n📊 Daily Statistics:")
        print(daily_stats)

        # Trend analysis
        print("\n📈 Trend Analysis:")
        first_day_avg = daily_stats["percent_short_mean"].iloc[0]
        last_day_avg = daily_stats["percent_short_mean"].iloc[-1]
        trend_change = last_day_avg - first_day_avg

        print(f"   Period: {start_date} to {end_date}")
        print(f"   Average short % change: {trend_change:+.2f}%")
        print(
            f"   Trend direction: {'📈 Increasing' if trend_change > 0 else '📉 Decreasing'}"
        )

        # Find stocks with consistent high short interest
        stock_consistency = (
            combined_df.groupby("asx_code")
            .agg({"percent_short": ["mean", "count", "std"], "date": "nunique"})
            .round(2)
        )

        stock_consistency.columns = [
            "_".join(col).strip() for col in stock_consistency.columns
        ]

        # Filter for stocks appearing on multiple days with high average short %
        consistent_high = stock_consistency[
            (stock_consistency["percent_short_mean"] > 15.0)
            & (stock_consistency["date_nunique"] >= 3)
        ].sort_values("percent_short_mean", ascending=False)

        if not consistent_high.empty:
            print("\n🎯 Consistently High Short Interest (>15%, 3+ days):")
            for stock, row in consistent_high.head(10).iterrows():
                print(
                    f"   {stock}: {row['percent_short_mean']:.2f}% avg "
                    f"({row['date_nunique']} days)"
                )

        return combined_df

    except (NotFoundError, FetchError) as e:
        print(f"❌ Error in time series analysis: {e}")
        return None


# Run time series analysis
time_series_df = time_series_analysis()

# %% [markdown]
"""
## 🚀 Advanced Pandas Operations
Demonstrate advanced pandas techniques like grouping, pivoting, and transformations.
"""


# %%
def advanced_pandas_operations(df: pd.DataFrame) -> None:
    """Demonstrate advanced pandas operations."""
    if df is None or df.empty:
        print("❌ No DataFrame available for advanced operations")
        return

    print("\n🚀 Advanced Pandas Operations")
    print("-" * 32)

    # Filter out non-numeric percent_short values and create categorical data for analysis
    df = df.copy()
    numeric_mask = pd.to_numeric(df["percent_short"], errors="coerce").notna()
    df = df[numeric_mask].copy()

    # Categorize by short interest level (using decimal thresholds)
    df["short_category"] = pd.cut(
        df["percent_short"],
        bins=[0, 0.05, 0.10, 0.20, float("inf")],  # Decimal format: 5%, 10%, 20%
        labels=["Low", "Medium", "High", "Extreme"],
    )

    # Categorize by market cap (if available)
    if "issued_shares" in df.columns:
        # Assume share price of $1 for simplicity (in real analysis, you'd get actual prices)
        df["estimated_market_cap"] = df["issued_shares"] * 1.0  # Simplified
        df["cap_category"] = pd.cut(
            df["estimated_market_cap"],
            bins=[0, 10_000_000, 100_000_000, 1_000_000_000, float("inf")],
            labels=["Micro", "Small", "Mid", "Large"],
        )

    # Group by analysis
    print("📊 Short Interest by Category:")
    category_stats = (
        df.groupby("short_category")
        .agg({"percent_short": ["count", "mean", "median"], "asx_code": "count"})
        .round(2)
    )

    category_stats.columns = ["_".join(col).strip() for col in category_stats.columns]
    print(category_stats)

    # Cross-tabulation
    if "cap_category" in df.columns:
        print("\n🔄 Cross-tabulation: Short Category vs Market Cap:")
        crosstab = pd.crosstab(df["short_category"], df["cap_category"], margins=True)
        print(crosstab)

    # Percentile analysis
    print("\n📈 Percentile Analysis:")
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    pct_values = df["percent_short"].quantile([p / 100 for p in percentiles])

    for pct, value in zip(percentiles, pct_values):
        print(f"   {pct:2d}th percentile: {value:.2f}%")

    # Rolling statistics (if we have time series data)
    if "date" in df.columns and len(df["date"].unique()) > 1:
        print("\n📊 Rolling Statistics (3-day window):")
        df_sorted = df.sort_values(["asx_code", "date"])
        df_sorted["rolling_mean"] = (
            df_sorted.groupby("asx_code")["percent_short"].rolling(3).mean().values
        )

        # Show stocks with significant rolling changes
        df_sorted["rolling_change"] = df_sorted.groupby("asx_code")[
            "rolling_mean"
        ].pct_change()
        significant_changes = df_sorted[abs(df_sorted["rolling_change"]) > 0.1].dropna()

        if not significant_changes.empty:
            print("   Stocks with >10% rolling average changes:")
            for _, row in significant_changes.head(5).iterrows():
                print(
                    f"   {row['asx_code']}: {row['rolling_change'] * 100:+.1f}% change"
                )

    # Outlier detection using IQR
    Q1 = df["percent_short"].quantile(0.25)
    Q3 = df["percent_short"].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    outliers = df[
        (df["percent_short"] < lower_bound) | (df["percent_short"] > upper_bound)
    ]
    print("\n🎯 Outlier Detection (IQR method):")
    print(f"   Normal range: {max(0, lower_bound):.2f}% - {upper_bound:.2f}%")
    print(f"   Outliers found: {len(outliers)}")

    if not outliers.empty:
        print("   Top outliers:")
        for _, row in outliers.nlargest(5, "percent_short").iterrows():
            print(f"   {row['asx_code']}: {row['percent_short']:.2f}%")


# Run advanced operations
if df is not None:
    advanced_pandas_operations(df)

# %% [markdown]
"""
## 💾 Data Export Examples
Demonstrate various data export formats and options.
"""


# %%
def export_data_examples(df: pd.DataFrame) -> None:
    """Demonstrate data export capabilities."""
    if df is None or df.empty:
        print("❌ No DataFrame available for export")
        return

    print("\n💾 Data Export Examples")
    print("-" * 22)

    # Prepare sample data for export
    export_df = df.head(100).copy()  # Limit to first 100 rows for demo

    try:
        # CSV export
        csv_file = "pandas_asx_shorts.csv"
        export_df.to_csv(csv_file, index=False)
        print(f"✅ Exported to CSV: {csv_file}")

        # JSON export
        json_file = "pandas_asx_shorts.json"
        export_df.to_json(json_file, orient="records", indent=2)
        print(f"✅ Exported to JSON: {json_file}")

        # Excel export (if openpyxl is available)
        try:
            excel_file = "pandas_asx_shorts.xlsx"
            with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
                export_df.to_excel(writer, sheet_name="Raw Data", index=False)

                # Add summary sheet
                summary = export_df.describe()
                summary.to_excel(writer, sheet_name="Summary")

            print(f"✅ Exported to Excel: {excel_file}")
        except ImportError:
            print("📊 Excel export requires openpyxl: pip install openpyxl")

        # Filtered exports
        high_short = export_df[export_df["percent_short"] > 10.0]
        if not high_short.empty:
            high_short_file = "pandas_high_short.csv"
            high_short.to_csv(high_short_file, index=False)
            print(f"✅ Exported high short interest stocks: {high_short_file}")

        print("\n📊 Export Summary:")
        print(f"   Total records exported: {len(export_df)}")
        print(
            f"   High short interest records: {len(high_short) if not high_short.empty else 0}"
        )

    except Exception as e:
        print(f"❌ Export error: {e}")


# Run export examples
if df is not None:
    export_data_examples(df)

# %% [markdown]
"""
## 📊 Visualization with Pandas
Create visualizations directly from pandas DataFrames.
"""


# %%
def create_pandas_visualizations(df: pd.DataFrame) -> None:
    """Create visualizations using pandas plotting capabilities."""
    if not HAS_PLOTTING or df is None or df.empty:
        print("❌ Plotting not available or no data")
        return

    print("\n📊 Pandas Visualization Examples")
    print("-" * 33)

    # Set up plotting
    plt.style.use("default")

    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle("ASX Short Selling Analysis - Pandas Integration", fontsize=14)

    # Plot 1: Histogram of short percentages
    df["percent_short"].hist(bins=30, ax=axes[0, 0], alpha=0.7, edgecolor="black")
    axes[0, 0].set_title("Distribution of Short Percentages")
    axes[0, 0].set_xlabel("Short Percentage (%)")
    axes[0, 0].set_ylabel("Frequency")
    axes[0, 0].grid(True, alpha=0.3)

    # Plot 2: Box plot of short percentages
    df.boxplot(column="percent_short", ax=axes[0, 1])
    axes[0, 1].set_title("Short Percentage Box Plot")
    axes[0, 1].set_ylabel("Short Percentage (%)")

    # Plot 3: Top 10 most shorted stocks
    top_10 = df.nlargest(10, "percent_short")
    top_10.plot(x="asx_code", y="percent_short", kind="bar", ax=axes[1, 0])
    axes[1, 0].set_title("Top 10 Most Shorted Stocks")
    axes[1, 0].set_xlabel("ASX Code")
    axes[1, 0].set_ylabel("Short Percentage (%)")
    axes[1, 0].tick_params(axis="x", rotation=45)

    # Plot 4: Scatter plot (if we have multiple numeric columns)
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) >= 2:
        x_col = numeric_cols[0]
        y_col = "percent_short"
        df.plot.scatter(x=x_col, y=y_col, ax=axes[1, 1], alpha=0.6)
        axes[1, 1].set_title(f"{y_col} vs {x_col}")
    else:
        # Alternative: show short percentage ranges
        short_ranges = pd.cut(df["percent_short"], bins=5)
        short_ranges.value_counts().plot(kind="pie", ax=axes[1, 1], autopct="%1.1f%%")
        axes[1, 1].set_title("Short Percentage Ranges")

    plt.tight_layout()
    plt.show()

    # Time series plot if we have date data
    if "date" in df.columns and len(df["date"].unique()) > 1:
        plt.figure(figsize=(12, 6))
        daily_avg = df.groupby("date")["percent_short"].mean()
        daily_avg.plot(kind="line", marker="o")
        plt.title("Average Short Percentage Over Time")
        plt.xlabel("Date")
        plt.ylabel("Average Short Percentage (%)")
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()


# Create visualizations
if df is not None:
    create_pandas_visualizations(df)

# %% [markdown]
"""
## 🎯 Summary and Best Practices

### What You've Learned:
- ✅ Converting ASX shorts data to pandas DataFrames
- ✅ Advanced filtering and statistical analysis
- ✅ Time series analysis and trend detection
- ✅ Complex grouping and aggregation operations
- ✅ Data export in multiple formats
- ✅ Visualization directly from DataFrames

### Pandas Best Practices:
- **Memory Efficiency**: Use appropriate data types and avoid unnecessary copies
- **Vectorization**: Leverage pandas vectorized operations instead of loops
- **Indexing**: Set meaningful indexes for better performance
- **Chaining**: Use method chaining for readable data transformations
- **Categorical Data**: Use categorical types for repeated string values

### Performance Tips:
- Use `query()` method for complex filtering
- Leverage `groupby` for aggregations
- Consider `eval()` for complex expressions
- Use `copy()` when modifying DataFrames to avoid warnings

### Next Steps:
- ⚡ **Polars Integration**: Try `04_polars_integration.py` for even faster processing
- 🚀 **Advanced Features**: Explore `05_advanced_features.py` for production patterns
- 📊 **Custom Analysis**: Build your own analysis pipelines

Happy data wrangling! 🐼
"""

# %%
print("\n" + "=" * 50)
print("🐼 Pandas Integration Examples Completed!")
print("... DataFrame operations, analysis, and visualization demonstrated")
print("🚀 Ready for high-performance analysis with Polars or advanced features")

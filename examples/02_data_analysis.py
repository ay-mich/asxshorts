# %% [markdown]
"""
# 📊 ASX Shorts Package - Data Analysis & Visualization

This script demonstrates advanced data analysis capabilities with the `asxshorts` package:

- 📈 **Statistical Analysis**: Calculate key metrics and distributions
- 📊 **Data Visualization**: Create charts and plots using matplotlib/seaborn
- 🔍 **Trend Analysis**: Analyze patterns across multiple days
- 🎯 **Short Squeeze Detection**: Identify potential trading opportunities
- 📋 **Comparative Analysis**: Compare stocks and time periods

## Prerequisites
```bash
pip install 'asxshorts' matplotlib seaborn
```
"""

# %% [markdown]
"""
## 📦 Setup and Imports
Import required modules and check for optional visualization libraries.
"""

# %%
import statistics
from datetime import date, timedelta
from typing import Any

from asxshorts import ShortsClient
from asxshorts.errors import FetchError, NotFoundError

# Optional imports for visualization
try:
    import matplotlib.pyplot as plt
    import seaborn as sns

    HAS_PLOTTING = True
    print("✅ Visualization libraries available")
except ImportError:
    HAS_PLOTTING = False
    print(
        "📊 Install matplotlib and seaborn for visualization: pip install matplotlib seaborn"
    )

# Initialize client
client = ShortsClient()
print("🚀 Data Analysis Examples - ASX Short Selling")
print("=" * 50)

# %% [markdown]
"""
## 📈 Single Day Analysis
Analyze short selling statistics for a specific date.
"""


# %%
def analyze_single_day(client: ShortsClient, target_date: date) -> dict[str, Any]:
    """Analyze short selling data for a single day."""
    print(f"\n📈 Analyzing data for {target_date}")

    try:
        result = client.fetch_day(target_date)

        if not result.records:
            print(f"❌ No data available for {target_date}")
            return {}

        # Extract short percentages (filter out non-numeric values)
        short_percentages = [
            rec.percent_short
            for rec in result.records
            if isinstance(rec.percent_short, (int, float))
        ]

        if not short_percentages:
            print(f"❌ No valid numeric data available for {target_date}")
            return {}

        # Calculate statistics
        stats = {
            "date": target_date,
            "total_stocks": len(result.records),
            "valid_stocks": len(short_percentages),
            "mean_short": statistics.mean(short_percentages),
            "median_short": statistics.median(short_percentages),
            "max_short": max(short_percentages),
            "min_short": min(short_percentages),
            "std_dev": statistics.stdev(short_percentages)
            if len(short_percentages) > 1
            else 0,
        }

        # Find highly shorted stocks (>10% = 0.10 in decimal format)
        highly_shorted = [
            rec
            for rec in result.records
            if isinstance(rec.percent_short, (int, float)) and rec.percent_short > 0.10
        ]

        print(f"📊 Statistics for {target_date}:")
        print(f"   Total stocks: {stats['total_stocks']}")
        print(f"   Valid stocks: {stats['valid_stocks']}")
        print(f"   Mean short %: {stats['mean_short'] * 100:.2f}%")
        print(f"   Median short %: {stats['median_short'] * 100:.2f}%")
        print(
            f"   Range: {stats['min_short'] * 100:.2f}% - {stats['max_short'] * 100:.2f}%"
        )
        print(f"   Standard deviation: {stats['std_dev'] * 100:.2f}%")
        print(f"   Highly shorted (>10%): {len(highly_shorted)} stocks")

        # Show top 5 most shorted (filter out non-numeric values)
        valid_records = [
            rec for rec in result.records if isinstance(rec.percent_short, (int, float))
        ]
        top_shorted = sorted(
            valid_records, key=lambda x: x.percent_short, reverse=True
        )[:5]
        print("\n🔥 Top 5 most shorted stocks:")
        for i, record in enumerate(top_shorted, 1):
            print(f"   {i}. {record.asx_code}: {record.percent_short * 100:.2f}%")

        return stats

    except (NotFoundError, FetchError) as e:
        print(f"❌ Error analyzing {target_date}: {e}")
        return {}


# Run single day analysis
target_date = date.today() - timedelta(days=20)
single_day_stats = analyze_single_day(client, target_date)

# %% [markdown]
"""
## 📊 Date Range Analysis
Analyze trends across multiple days to identify patterns.
"""


# %%
def analyze_date_range(
    client: ShortsClient, start_date: date, end_date: date
) -> list[dict[str, Any]]:
    """Analyze short selling data across a date range."""
    print(f"\n📊 Analyzing date range: {start_date} to {end_date}")

    try:
        range_result = client.fetch_range(start_date, end_date)
        daily_stats = []

        for date_key, daily_result in range_result.results.items():
            if daily_result.records:
                # Filter out non-numeric percent_short values (e.g., "-" strings)
                short_percentages = [
                    rec.percent_short
                    for rec in daily_result.records
                    if isinstance(rec.percent_short, (int, float))
                ]

                if short_percentages:  # Only calculate stats if we have numeric data
                    stats = {
                        "date": date_key,
                        "total_stocks": len(daily_result.records),
                        "valid_stocks": len(short_percentages),
                        "mean_short": statistics.mean(short_percentages),
                        "median_short": statistics.median(short_percentages),
                        "max_short": max(short_percentages),
                        "min_short": min(short_percentages),
                        "highly_shorted_count": len(
                            [p for p in short_percentages if p > 0.10]
                        ),  # Fixed: 0.10 for 10%
                    }
                else:
                    # Handle case where no valid numeric data exists
                    stats = {
                        "date": date_key,
                        "total_stocks": len(daily_result.records),
                        "valid_stocks": 0,
                        "mean_short": 0.0,
                        "median_short": 0.0,
                        "max_short": 0.0,
                        "min_short": 0.0,
                        "highly_shorted_count": 0,
                    }
                daily_stats.append(stats)

        # Print summary
        if daily_stats:
            print(f"✅ Analyzed {len(daily_stats)} days of data")
            avg_mean = statistics.mean([s["mean_short"] for s in daily_stats])
            avg_highly_shorted = statistics.mean(
                [s["highly_shorted_count"] for s in daily_stats]
            )

            print("📈 Range Summary:")
            print(f"   Average daily mean short %: {avg_mean:.2f}%")
            print(f"   Average highly shorted stocks per day: {avg_highly_shorted:.1f}")

            # Show daily breakdown
            print("\n📅 Daily breakdown:")
            for stats in daily_stats:
                print(
                    f"   {stats['date']}: {stats['mean_short']:.2f}% avg, {stats['highly_shorted_count']} highly shorted"
                )

        return daily_stats

    except (NotFoundError, FetchError) as e:
        print(f"❌ Error analyzing range: {e}")
        return []


# Run date range analysis
end_date = target_date
start_date = end_date - timedelta(days=7)
daily_stats = analyze_date_range(client, start_date, end_date)

# %% [markdown]
"""
## 📊 Data Visualization
Create charts and plots to visualize short selling patterns.
"""


# %%
def create_visualizations(daily_stats: list[dict[str, Any]]) -> None:
    """Create visualizations of short selling data."""
    if not HAS_PLOTTING:
        print(
            "❌ Visualization libraries not available. Install with: pip install matplotlib seaborn"
        )
        return

    if not daily_stats:
        print("❌ No data available for visualization")
        return

    print("\n📊 Creating visualizations...")

    # Set up the plotting style
    plt.style.use("default")
    sns.set_palette("husl")

    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle("ASX Short Selling Analysis", fontsize=16, fontweight="bold")

    # Extract data for plotting
    dates = [stats["date"] for stats in daily_stats]
    mean_shorts = [stats["mean_short"] for stats in daily_stats]
    highly_shorted_counts = [stats["highly_shorted_count"] for stats in daily_stats]
    max_shorts = [stats["max_short"] for stats in daily_stats]
    total_stocks = [stats["total_stocks"] for stats in daily_stats]

    # Plot 1: Mean short percentage over time
    axes[0, 0].plot(dates, mean_shorts, marker="o", linewidth=2, markersize=6)
    axes[0, 0].set_title("Average Short % Over Time")
    axes[0, 0].set_ylabel("Short Percentage (%)")
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].tick_params(axis="x", rotation=45)

    # Plot 2: Highly shorted stocks count
    axes[0, 1].bar(range(len(dates)), highly_shorted_counts, alpha=0.7)
    axes[0, 1].set_title("Highly Shorted Stocks (>10%) Count")
    axes[0, 1].set_ylabel("Number of Stocks")
    axes[0, 1].set_xticks(range(len(dates)))
    axes[0, 1].set_xticklabels([d.strftime("%m-%d") for d in dates], rotation=45)
    axes[0, 1].grid(True, alpha=0.3)

    # Plot 3: Maximum short percentage
    axes[1, 0].plot(
        dates, max_shorts, marker="s", color="red", linewidth=2, markersize=6
    )
    axes[1, 0].set_title("Maximum Short % Per Day")
    axes[1, 0].set_ylabel("Short Percentage (%)")
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].tick_params(axis="x", rotation=45)

    # Plot 4: Total stocks tracked
    axes[1, 1].plot(
        dates, total_stocks, marker="^", color="green", linewidth=2, markersize=6
    )
    axes[1, 1].set_title("Total Stocks Tracked")
    axes[1, 1].set_ylabel("Number of Stocks")
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.show()

    # Create distribution plot for the most recent day
    if daily_stats:
        latest_date = daily_stats[-1]["date"]
        print(f"\n📊 Creating distribution plot for {latest_date}...")

        try:
            result = client.fetch_day(latest_date)
            if result.records:
                short_percentages = [rec.percent_short for rec in result.records]

                plt.figure(figsize=(12, 6))

                # Histogram
                plt.subplot(1, 2, 1)
                plt.hist(short_percentages, bins=30, alpha=0.7, edgecolor="black")
                plt.title(f"Short % Distribution - {latest_date}")
                plt.xlabel("Short Percentage (%)")
                plt.ylabel("Number of Stocks")
                plt.grid(True, alpha=0.3)

                # Box plot
                plt.subplot(1, 2, 2)
                plt.boxplot(short_percentages)
                plt.title(f"Short % Box Plot - {latest_date}")
                plt.ylabel("Short Percentage (%)")
                plt.grid(True, alpha=0.3)

                plt.tight_layout()
                plt.show()

        except Exception as e:
            print(f"❌ Error creating distribution plot: {e}")


# Create visualizations
create_visualizations(daily_stats)

# %% [markdown]
"""
## 🎯 Short Squeeze Candidate Detection
Identify stocks with high short interest that might be squeeze candidates.
"""


# %%
def find_short_squeeze_candidates(
    client: ShortsClient, target_date: date, threshold: float = 15.0
) -> None:
    """Find potential short squeeze candidates based on high short interest."""
    print(f"\n🎯 Finding short squeeze candidates for {target_date}")
    print(f"   Threshold: >{threshold}% short interest")

    try:
        result = client.fetch_day(target_date)

        if not result.records:
            print(f"❌ No data available for {target_date}")
            return

        # Filter for high short interest (convert threshold to decimal format)
        threshold_decimal = threshold / 100.0  # Convert 15.0% to 0.15
        candidates = [
            rec
            for rec in result.records
            if isinstance(rec.percent_short, (int, float))
            and rec.percent_short > threshold_decimal
        ]

        # Sort by short percentage (highest first)
        candidates.sort(key=lambda x: x.percent_short, reverse=True)

        print(f"🔍 Found {len(candidates)} potential candidates:")

        if candidates:
            print("\n🚨 Top short squeeze candidates:")
            for i, candidate in enumerate(candidates[:10], 1):  # Show top 10
                # Calculate additional metrics if available
                short_ratio = ""
                if hasattr(candidate, "short_sold") and hasattr(
                    candidate, "issued_shares"
                ):
                    if candidate.short_sold and candidate.issued_shares:
                        ratio = candidate.short_sold / candidate.issued_shares * 100
                        short_ratio = f" (ratio: {ratio:.2f}%)"

                print(
                    f"   {i:2d}. {candidate.asx_code:6s}: {candidate.percent_short * 100:6.2f}%{short_ratio}"
                )

            # Additional analysis
            avg_short = statistics.mean([c.percent_short for c in candidates])
            max_short = max([c.percent_short for c in candidates])

            print("\n📊 Candidate Statistics:")
            print(f"   Average short %: {avg_short * 100:.2f}%")
            print(f"   Maximum short %: {max_short * 100:.2f}%")
            print(f"   Stocks above {threshold}%: {len(candidates)}")

            # Risk warning
            print("\n⚠️  Risk Warning:")
            print("   High short interest doesn't guarantee a squeeze")
            print("   Consider volume, market cap, and fundamental analysis")
            print("   Short squeezes are high-risk, high-reward scenarios")
        else:
            print(f"   No stocks found with >{threshold}% short interest")

    except (NotFoundError, FetchError) as e:
        print(f"❌ Error finding candidates: {e}")


# Find short squeeze candidates
find_short_squeeze_candidates(client, target_date, threshold=15.0)

# %% [markdown]
"""
## 📋 Comparative Analysis
Compare different time periods and identify trends.
"""


# %%
def comparative_analysis(daily_stats: list[dict[str, Any]]) -> None:
    """Perform comparative analysis across the date range."""
    if len(daily_stats) < 2:
        print("❌ Need at least 2 days of data for comparative analysis")
        return

    print(f"\n📋 Comparative Analysis ({len(daily_stats)} days)")
    print("-" * 40)

    # Calculate trends
    first_day = daily_stats[0]
    last_day = daily_stats[-1]

    mean_change = last_day["mean_short"] - first_day["mean_short"]
    highly_shorted_change = (
        last_day["highly_shorted_count"] - first_day["highly_shorted_count"]
    )

    print("📈 Trend Analysis:")
    print(f"   Period: {first_day['date']} to {last_day['date']}")
    print(f"   Mean short % change: {mean_change:+.2f}%")
    print(f"   Highly shorted count change: {highly_shorted_change:+d}")

    # Find most volatile day
    volatility_scores = []
    for stats in daily_stats:
        if "max_short" in stats and "min_short" in stats:
            volatility = stats["max_short"] - stats["min_short"]
            volatility_scores.append((stats["date"], volatility))

    if volatility_scores:
        most_volatile = max(volatility_scores, key=lambda x: x[1])
        print(
            f"   Most volatile day: {most_volatile[0]} (range: {most_volatile[1]:.2f}%)"
        )

    # Calculate correlations if we have enough data
    if len(daily_stats) >= 3:
        means = [s["mean_short"] for s in daily_stats]
        highly_shorted = [s["highly_shorted_count"] for s in daily_stats]

        # Simple correlation calculation
        if len(set(means)) > 1 and len(set(highly_shorted)) > 1:
            mean_trend = "increasing" if means[-1] > means[0] else "decreasing"
            hs_trend = (
                "increasing" if highly_shorted[-1] > highly_shorted[0] else "decreasing"
            )

            print(f"   Mean short % trend: {mean_trend}")
            print(f"   Highly shorted count trend: {hs_trend}")


# Run comparative analysis
comparative_analysis(daily_stats)

# %% [markdown]
"""
## 🎯 Summary and Insights

### Key Takeaways:
- ✅ Statistical analysis reveals market short selling patterns
- ✅ Visualization helps identify trends and outliers
- ✅ Short squeeze candidates can be systematically identified
- ✅ Comparative analysis shows market evolution over time

### Next Steps:
- 🐼 **Pandas Integration**: Use `03_pandas_integration.py` for DataFrame operations
- ⚡ **Polars Integration**: Try `04_polars_integration.py` for high-performance analysis
- 🚀 **Advanced Features**: Explore `05_advanced_features.py` for production patterns

### Analysis Best Practices:
- Always validate data availability before analysis
- Use multiple metrics for comprehensive insights
- Consider market context when interpreting results
- Combine quantitative analysis with fundamental research

Happy analyzing! 📊
"""

# %%
print("\n" + "=" * 50)
print("📊 Data Analysis Examples Completed!")
print("... Statistical analysis, visualization, and trend detection demonstrated")
print("🎯 Ready for more advanced analysis with pandas or polars integration")

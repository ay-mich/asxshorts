# %% [markdown]
"""
# 🚀 ASX Shorts Package - Basic Usage Examples

This script demonstrates the fundamental features of the `asxshorts` package:

- 📦 **Client Creation**: Initialize the ShortsClient
- 📅 **Single Day Fetching**: Get short selling data for a specific date
- 📊 **Date Range Fetching**: Retrieve data across multiple days
- 🛡️ **Error Handling**: Handle common exceptions gracefully
- ⚡ **Cache Performance**: Understand caching behaviour

## Prerequisites
```bash
pip install 'asxshorts'
```

## Quick Start
Run each cell individually in your IDE (VS Code, PyCharm, etc.) to see the results.
"""

# %% [markdown]
"""
## 📦 Setup and Imports
Import the necessary modules and set up the client.
"""

# %%
from datetime import date, timedelta

from asxshorts import ShortsClient
from asxshorts.errors import FetchError, NotFoundError

print("🚀 ASX Shorts Package - Basic Usage Examples")
print("=" * 50)

# %% [markdown]
"""
## 🔧 Client Initialization
Create a ShortsClient instance. This handles all data fetching and caching automatically.
"""

# %%
# Create the client - this is your main interface to ASX short selling data
client = ShortsClient()
print("✅ ShortsClient initialized successfully!")

# %% [markdown]
"""
## 📅 Example 1: Fetch Single Day Data
Retrieve short selling data for a specific date. We'll use a recent business day.
"""

# %%
# Use a recent business day (20 days ago to ensure data exists)
target_date = date.today() - timedelta(days=20)
print(f"📅 Fetching data for: {target_date}")

try:
    # Fetch data for the target date
    result = client.fetch_day(target_date)

    print(f"✅ Success! Found {result.record_count} records")
    print(f"🗄️ Data source: {'Cache' if result.from_cache else 'Network'}")

    # Display first few records to see the data structure
    if result.records:
        print(f"\n📊 Sample records (showing first 3 of {len(result.records)}):")
        for i, record in enumerate(result.records[:3]):
            print(f"  {i + 1}. {record.asx_code}: {record.percent_short:.2f}% short")

except NotFoundError:
    print(f"❌ No data available for {target_date} (likely weekend/holiday)")
except FetchError as e:
    print(f"❌ Failed to fetch data: {e}")

# %% [markdown]
"""
## 📊 Example 2: Fetch Date Range Data
Retrieve data across multiple days to analyze trends.
"""

# %%
# Define date range (last few business days)
end_date = target_date
start_date = end_date - timedelta(days=4)  # Extra days to account for weekends

print(f"📊 Fetching data range: {start_date} to {end_date}")

try:
    # Fetch data for the date range
    range_result = client.fetch_range(start_date, end_date)

    print(f"✅ Success! Found {range_result.total_records} total records")
    print(f"📅 Date range covers {len(range_result.results)} days")

    # Show summary by date
    print("\n📈 Daily breakdown:")
    for date_key, daily_result in range_result.results.items():
        cache_status = "💾" if daily_result.from_cache else "🌐"
        print(f"  {date_key}: {daily_result.record_count} records {cache_status}")

except FetchError as e:
    print(f"❌ Failed to fetch range data: {e}")

# %% [markdown]
"""
## ⚡ Example 3: Cache Performance Demo
Demonstrate how caching improves performance on subsequent requests.
"""

# %%
import time

print("⚡ Cache Performance Demonstration")
print("-" * 35)

# First fetch (will cache the data)
print(f"🌐 First fetch for {target_date} (from network)...")
start_time = time.time()
try:
    first_result = client.fetch_day(target_date)
    first_duration = time.time() - start_time
    print(f"✅ Completed in {first_duration:.4f} seconds")
except Exception as e:
    print(f"❌ Error: {e}")
    first_duration = None

# Second fetch (should use cache)
print(f"\n💾 Second fetch for {target_date} (from cache)...")
start_time = time.time()
try:
    second_result = client.fetch_day(target_date)
    second_duration = time.time() - start_time
    print(f"✅ Completed in {second_duration:.4f} seconds")

    # Calculate speedup
    if first_duration and second_duration > 0:
        speedup = first_duration / second_duration
        print(f"🚀 Cache speedup: {speedup:.1f}x faster!")

except Exception as e:
    print(f"❌ Error: {e}")

# %% [markdown]
"""
## 🛡️ Example 4: Error Handling Patterns
Learn how to handle different types of errors gracefully.
"""


# %%
def demonstrate_error_handling():
    """Show different error scenarios and how to handle them."""
    print("🛡️ Error Handling Examples")
    print("-" * 26)

    # Test scenarios
    test_cases = [
        ("Recent date", date.today() - timedelta(days=1)),
        ("Weekend date", date(2024, 1, 6)),  # Saturday
        ("Very old date", date(2020, 1, 1)),  # Likely no data
    ]

    for description, test_date in test_cases:
        print(f"\n🧪 Testing {description}: {test_date}")

        try:
            result = client.fetch_day(test_date)
            print(f"   ✅ Success: {result.record_count} records")

        except NotFoundError:
            print("   📅 No data available (weekend/holiday/no trading)")

        except FetchError as e:
            print(f"   ⚠️ Fetch error: {e}")

        except Exception as e:
            print(f"   ❌ Unexpected error: {type(e).__name__}: {e}")


# Run the error handling demo
demonstrate_error_handling()

# %% [markdown]
"""
## 🎯 Summary and Next Steps

### What You've Learned:
- ✅ How to create and use a `ShortsClient`
- ✅ Fetching single-day and date-range data
- ✅ Understanding cache behavior and performance benefits
- ✅ Proper error handling for robust applications

### Next Steps:
- 📊 **Data Analysis**: Run `02_data_analysis.py` for visualization examples
- 🐼 **Pandas Integration**: See `03_pandas_integration.py` for DataFrame operations
- ⚡ **Polars Integration**: Check `04_polars_integration.py` for high-performance processing
- 🚀 **Advanced Features**: Explore `05_advanced_features.py` for production patterns

### Key Takeaways:
- The package handles caching automatically for better performance
- Always wrap fetch operations in try-catch blocks
- Use date ranges for trend analysis across multiple days
- Cache provides significant performance improvements for repeated requests

Happy analyzing! 📈
"""

# %%

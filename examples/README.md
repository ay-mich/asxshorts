# ASX Shorts Examples

This directory contains comprehensive examples and tutorials for the [`asxshorts`](https://pypi.org/project/asxshorts/) Python package - a simple and efficient library for fetching Australian Securities Exchange (ASX) short selling data.

## 📁 Directory Structure

```
├── 01_basic_usage.py          # Getting started with the basics
├── 02_data_analysis.py        # Data analysis and visualization
├── 03_pandas_integration.py   # Working with pandas DataFrames
├── 04_polars_integration.py   # Working with polars DataFrames
├── 05_advanced_features.py    # Advanced features and production patterns
├── requirements.txt           # Dependencies for examples
└── README.md                  # This file
```

## 📚 Examples Overview

| Script                     | Description                                  | Key Features                                             |
| -------------------------- | -------------------------------------------- | -------------------------------------------------------- |
| `01_basic_usage.py`        | Essential operations and basic API usage     | Client setup, single day fetch, date ranges, caching     |
| `02_data_analysis.py`      | Data analysis and visualization examples     | Matplotlib/seaborn charts, trend analysis, statistics    |
| `03_pandas_integration.py` | Integration with pandas ecosystem            | DataFrames, filtering, aggregations, Excel export        |
| `04_polars_integration.py` | High-performance data processing with polars | Fast operations, lazy evaluation, performance comparison |
| `05_advanced_features.py`  | Advanced features and production patterns    | Cache management, error handling, validation, monitoring |

## 🏃‍♂️ Running the Examples

### Prerequisites

You should install the package dependencies first. You can install the `asxshorts` package in editable mode along with the optional pandas and polars dependencies, or install the specific requirements for these examples:

```bash
# From the repository root, install the package in editable mode:
pip install -e .[pandas,polars]

# Install additional requirements for visualization and notebooks:
pip install -r examples/requirements.txt
```

### Running Python Scripts

From the repository root:

```bash
# Run any example script
python examples/01_basic_usage.py

# Or run all examples
for script in examples/*.py; do
    echo "Running $script..."
    python "$script"
    echo "---"
done
```

## 📄 License

These examples are provided under the MIT License. See the main `LICENSE` file for details.

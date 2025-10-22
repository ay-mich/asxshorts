"""CSV parsing with header normalization and type coercion."""

import csv
import logging
import re
from datetime import date
from io import StringIO
from typing import Any

from .errors import ParseError

logger = logging.getLogger(__name__)

# Column mapping from various CSV formats to normalized names
COLUMN_MAP = {
    # Standard mappings
    "product": "asx_code",  # Product often contains the ASX code
    "product_code": "asx_code",
    "reported_short_positions": "short_sold",
    "total_product_in_issue": "issued_shares",
    "percent_short": "percent_short",
    # Alternative column names
    "company": "company_name",
    "company_name": "company_name",
    "security": "company_name",
    "security_name": "company_name",
    "code": "asx_code",
    "symbol": "asx_code",
    "ticker": "asx_code",
    "asx_code": "asx_code",
    "short_sold": "short_sold",
    "short_positions": "short_sold",
    "reported_short_pos": "short_sold",
    "short_selling": "short_sold",
    "short_qty": "short_sold",
    "issued_shares": "issued_shares",
    "total_issued": "issued_shares",
    "total_product_issued": "issued_shares",
    "shares_on_issue": "issued_shares",
    "issued_qty": "issued_shares",
    "percent_short_sold": "percent_short",
    "percentage_short": "percent_short",
    "short_percentage": "percent_short",
    "percent_of_total_product_in_issue_reported_as_short_positions": "percent_short",
}

# Expected output columns
EXPECTED_COLUMNS = [
    "report_date",
    "asx_code",
    "company_name",
    "short_sold",
    "issued_shares",
    "percent_short",
]

# Columns that should be converted to numeric types
NUMERIC_COLUMNS = ["short_sold", "issued_shares", "percent_short"]


def normalize_column_name(col_name: str) -> str:
    """Normalize column name to snake_case format."""
    if not col_name:
        return ""

    # Clean the column name
    name = col_name.strip().lower()

    # Replace % with percent
    name = name.replace("%", "percent")

    # Replace spaces and other separators with underscores
    name = re.sub(r"[\s\-\.]+", "_", name)

    # Remove non-alphanumeric characters except underscores
    name = re.sub(r"[^a-z0-9_]", "", name)

    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)

    # Remove leading/trailing underscores
    name = name.strip("_")

    return name


def detect_delimiter(content: str) -> str:
    """Detect CSV delimiter by analyzing the content."""
    # Take first few lines for analysis
    lines = content.split("\n")[:5]
    sample = "\n".join(line for line in lines if line.strip())

    # Count occurrences of common delimiters
    comma_count = sample.count(",")
    tab_count = sample.count("\t")
    semicolon_count = sample.count(";")
    pipe_count = sample.count("|")

    # Return the most frequent delimiter
    delimiter_counts = {
        ",": comma_count,
        "\t": tab_count,
        ";": semicolon_count,
        "|": pipe_count,
    }

    delimiter = max(delimiter_counts, key=lambda x: delimiter_counts[x])
    logger.debug(f"Detected delimiter: '{delimiter}' (counts: {delimiter_counts})")

    return delimiter


def clean_numeric_value(value: Any) -> str:
    """Clean numeric value by removing formatting characters."""
    if not isinstance(value, str):
        return str(value)

    # Remove common formatting
    cleaned = value.strip()

    # Remove thousands separators
    cleaned = cleaned.replace(",", "")
    cleaned = cleaned.replace(" ", "")

    # Remove percentage symbols
    cleaned = cleaned.replace("%", "")

    # Remove currency symbols
    cleaned = cleaned.replace("$", "")
    cleaned = cleaned.replace("A$", "")

    return cleaned


def coerce_to_int(value: Any) -> int | str | None:
    """Try to convert value to int, return original if failed."""
    if value is None or value == "":
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        cleaned = clean_numeric_value(value)
        if not cleaned:
            return value  # Return original for non-numeric strings like "N/A"

        try:
            return int(float(cleaned))  # Handle cases like "123.0"
        except (ValueError, TypeError):
            return value  # Keep original if conversion fails

    return str(value)


def coerce_to_float(value: Any) -> float | str | None:
    """Try to convert value to float, return original if failed."""
    if value is None or value == "":
        return None

    if isinstance(value, float):
        return value

    if isinstance(value, int):
        return float(value)

    if isinstance(value, str):
        cleaned = clean_numeric_value(value)
        if not cleaned:
            return value  # Return original for non-numeric strings like "N/A"

        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return value  # Keep original if conversion fails

    return str(value)


def parse_csv_content(content: bytes, report_date: date) -> list[dict[str, Any]]:
    """Parse CSV content and return normalized records."""
    try:
        # Decode content
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text_content = content.decode("latin1")
            except UnicodeDecodeError:
                text_content = content.decode("utf-8", errors="replace")

        if not text_content.strip():
            logger.warning(f"Empty CSV content for {report_date}")
            return []

        # Detect delimiter
        delimiter = detect_delimiter(text_content)

        # Parse CSV
        csv_reader = csv.DictReader(StringIO(text_content), delimiter=delimiter)

        # Get and normalize headers
        if not csv_reader.fieldnames:
            raise ParseError(f"No headers found in CSV for {report_date}")

        original_headers = csv_reader.fieldnames
        normalized_headers = [normalize_column_name(h) for h in original_headers]

        logger.debug(f"Original headers: {original_headers}")
        logger.debug(f"Normalized headers: {normalized_headers}")

        # Create header mapping
        header_mapping = {}
        for orig, norm in zip(original_headers, normalized_headers, strict=True):
            header_mapping[orig] = COLUMN_MAP.get(norm, norm)

        logger.debug(f"Header mapping: {header_mapping}")

        # Parse rows
        records = []
        for row_num, row in enumerate(csv_reader, 1):
            try:
                record = {}

                # Map columns
                for orig_col, value in row.items():
                    if orig_col in header_mapping:
                        mapped_col = header_mapping[orig_col]
                        record[mapped_col] = value

                # Ensure all expected columns exist
                for col in EXPECTED_COLUMNS:
                    if col not in record:
                        record[col] = None

                # Add report date
                record["report_date"] = report_date.strftime("%Y-%m-%d")

                # Type coercion for numeric columns
                if "short_sold" in record:
                    record["short_sold"] = coerce_to_int(record["short_sold"])

                if "issued_shares" in record:
                    record["issued_shares"] = coerce_to_int(record["issued_shares"])

                if "percent_short" in record:
                    record["percent_short"] = coerce_to_float(record["percent_short"])

                # Clean up ASX code
                if record.get("asx_code"):
                    record["asx_code"] = str(record["asx_code"]).strip().upper()

                # Skip rows with no ASX code
                if not record.get("asx_code"):
                    continue

                records.append(record)

            except Exception as e:
                logger.warning(f"Error parsing row {row_num} for {report_date}: {e}")
                continue

        logger.info(f"Parsed {len(records)} records for {report_date}")
        return records

    except Exception as e:
        raise ParseError(
            f"Failed to parse CSV for {report_date}", report_date, str(e)
        ) from e


def validate_records(
    records: list[dict[str, Any]], report_date: date
) -> list[dict[str, Any]]:
    """Validate and clean parsed records."""
    valid_records = []

    for record in records:
        # Skip records without essential data
        if not record.get("asx_code"):
            continue

        # Validate numeric ranges
        if isinstance(record.get("percent_short"), (int, float)):
            # Clamp percentage to reasonable range (0-1000%)
            if record["percent_short"] < 0:
                record["percent_short"] = 0
            elif record["percent_short"] > 1000:
                logger.warning(
                    f"Clamping high percent_short value: {record['percent_short']} for {record['asx_code']}"
                )
                record["percent_short"] = 1000

        valid_records.append(record)

    logger.debug(f"Validated {len(valid_records)} records for {report_date}")
    return valid_records

"""Tests for asxshorts.parse module."""

from datetime import date

from asxshorts.parse import (
    clean_numeric_value,
    coerce_to_float,
    coerce_to_int,
    detect_delimiter,
    parse_csv_content,
    validate_records,
)


class TestDetectDelimiter:
    """Test delimiter detection functionality."""

    def test_comma_delimiter(self):
        """Test detection of comma delimiter."""
        content = "col1,col2,col3\nvalue1,value2,value3"
        delimiter = detect_delimiter(content)
        assert delimiter == ","

    def test_pipe_delimiter(self):
        """Test detection of pipe delimiter."""
        content = "col1|col2|col3\nvalue1|value2|value3"
        delimiter = detect_delimiter(content)
        assert delimiter == "|"

    def test_tab_delimiter(self):
        """Test detection of tab delimiter."""
        content = "col1\tcol2\tcol3\nvalue1\tvalue2\tvalue3"
        delimiter = detect_delimiter(content)
        assert delimiter == "\t"

    def test_semicolon_delimiter(self):
        """Test detection of semicolon delimiter."""
        content = "col1;col2;col3\nvalue1;value2;value3"
        delimiter = detect_delimiter(content)
        assert delimiter == ";"

    def test_default_delimiter(self):
        """Test default delimiter when none detected."""
        content = "col1 col2 col3\nvalue1 value2 value3"
        delimiter = detect_delimiter(content)
        assert delimiter == ","  # Should default to comma

    def test_empty_content(self):
        """Test delimiter detection with empty content."""
        delimiter = detect_delimiter("")
        assert delimiter == ","

    def test_single_line_content(self):
        """Test delimiter detection with single line."""
        content = "col1,col2,col3"
        delimiter = detect_delimiter(content)
        assert delimiter == ","


class TestCleanNumericValue:
    """Test numeric value cleaning functionality."""

    def test_clean_comma_separated(self):
        """Test cleaning comma-separated numbers."""
        assert clean_numeric_value("1,000,000") == "1000000"
        assert clean_numeric_value("1,234.56") == "1234.56"

    def test_clean_space_separated(self):
        """Test cleaning space-separated numbers."""
        assert clean_numeric_value("1 000 000") == "1000000"
        assert clean_numeric_value("1 234.56") == "1234.56"

    def test_clean_percentage(self):
        """Test cleaning percentage values."""
        assert clean_numeric_value("50%") == "50"
        assert clean_numeric_value("12.5%") == "12.5"

    def test_clean_whitespace(self):
        """Test cleaning whitespace."""
        assert clean_numeric_value("  123.45  ") == "123.45"
        assert clean_numeric_value("\t456\n") == "456"

    def test_clean_combined(self):
        """Test cleaning combined formatting."""
        assert clean_numeric_value("  1,234.56%  ") == "1234.56"
        assert clean_numeric_value("\t1 000 000%\n") == "1000000"

    def test_clean_already_clean(self):
        """Test cleaning already clean values."""
        assert clean_numeric_value("123") == "123"
        assert clean_numeric_value("123.45") == "123.45"

    def test_clean_empty_string(self):
        """Test cleaning empty string."""
        assert clean_numeric_value("") == ""
        assert clean_numeric_value("   ") == ""

    def test_clean_non_numeric(self):
        """Test cleaning non-numeric values."""
        assert clean_numeric_value("abc") == "abc"
        assert clean_numeric_value("N/A") == "N/A"


class TestCoerceToInt:
    """Test integer coercion functionality."""

    def test_coerce_valid_int(self):
        """Test coercing valid integers."""
        assert coerce_to_int("123") == 123
        assert coerce_to_int("0") == 0
        assert coerce_to_int("-456") == -456

    def test_coerce_float_to_int(self):
        """Test coercing float strings to int."""
        assert coerce_to_int("123.0") == 123
        assert coerce_to_int("456.00") == 456

    def test_coerce_formatted_numbers(self):
        """Test coercing formatted numbers."""
        assert coerce_to_int("1,000") == 1000
        assert coerce_to_int("1 000 000") == 1000000

    def test_coerce_invalid_values(self):
        """Test coercing invalid values returns original."""
        assert coerce_to_int("abc") == "abc"
        assert coerce_to_int("123.45") == 123  # Float gets converted to int
        assert coerce_to_int("") is None
        assert coerce_to_int("N/A") == "N/A"

    def test_coerce_none(self):
        """Test coercing None returns None."""
        assert coerce_to_int(None) is None


class TestCoerceToFloat:
    """Test float coercion functionality."""

    def test_coerce_valid_float(self):
        """Test coercing valid floats."""
        assert coerce_to_float("123.45") == 123.45
        assert coerce_to_float("0.0") == 0.0
        assert coerce_to_float("-456.78") == -456.78

    def test_coerce_int_to_float(self):
        """Test coercing integer strings to float."""
        assert coerce_to_float("123") == 123.0
        assert coerce_to_float("0") == 0.0

    def test_coerce_formatted_numbers(self):
        """Test coercing formatted numbers."""
        assert coerce_to_float("1,234.56") == 1234.56
        assert coerce_to_float("1 000.5") == 1000.5

    def test_coerce_percentage(self):
        """Test coercing percentage values."""
        assert coerce_to_float("50%") == 50.0
        assert coerce_to_float("12.5%") == 12.5

    def test_coerce_invalid_values(self):
        """Test coercing invalid values returns original."""
        assert coerce_to_float("abc") == "abc"
        assert coerce_to_float("") is None
        assert coerce_to_float("N/A") == "N/A"

    def test_coerce_none(self):
        """Test coercing None returns None."""
        assert coerce_to_float(None) is None


class TestParseCsvContent:
    """Test CSV content parsing functionality."""

    def test_parse_basic_csv(self):
        """Test parsing basic CSV content."""
        content = b"Product,Short Qty,Issued Qty\nCBA,1000,100000\nANZ,2000,200000"
        test_date = date(2024, 1, 15)

        records = parse_csv_content(content, test_date)

        assert len(records) == 2
        assert records[0]["asx_code"] == "CBA"  # Product maps to asx_code
        assert (
            records[0]["short_sold"] == 1000
        )  # Short Qty maps to short_sold and gets coerced to int
        assert records[1]["asx_code"] == "ANZ"

    def test_parse_with_different_delimiter(self):
        """Test parsing CSV with different delimiter."""
        content = b"Product|Short Qty|Issued Qty\nCBA|1000|100000"
        test_date = date(2024, 1, 15)

        records = parse_csv_content(content, test_date)

        assert len(records) == 1
        assert records[0]["asx_code"] == "CBA"

    def test_parse_empty_content(self):
        """Test parsing empty content."""
        content = b""
        test_date = date(2024, 1, 15)

        records = parse_csv_content(content, test_date)
        assert records == []

    def test_parse_header_only(self):
        """Test parsing content with header only."""
        content = b"Product,Short Qty,Issued Qty"
        test_date = date(2024, 1, 15)

        records = parse_csv_content(content, test_date)
        assert records == []

    def test_parse_with_quotes(self):
        """Test parsing CSV with quoted values."""
        content = b'Product,Company Name,Short Qty\nCBA,"Commonwealth Bank",1000'
        test_date = date(2024, 1, 15)

        records = parse_csv_content(content, test_date)

        assert len(records) == 1
        assert records[0]["company_name"] == "Commonwealth Bank"

    def test_parse_with_empty_fields(self):
        """Test parsing CSV with empty fields."""
        content = b"Product,Short Qty,Issued Qty\nCBA,,100000\nANZ,2000,"
        test_date = date(2024, 1, 15)

        records = parse_csv_content(content, test_date)

        assert len(records) == 2
        assert records[0]["short_sold"] is None  # Empty short qty becomes None
        assert records[1]["asx_code"] == "ANZ"

    def test_parse_malformed_csv(self):
        """Test parsing malformed CSV content."""
        content = (
            b"Product,Short Qty\nCBA,1000,extra_field\nANZ"  # Inconsistent columns
        )
        test_date = date(2024, 1, 15)

        # Should handle gracefully and parse what it can
        records = parse_csv_content(content, test_date)
        assert len(records) >= 0  # Should not crash

    def test_parse_unicode_content(self):
        """Test parsing CSV with unicode content."""
        content = "Product,Company Name\nCBA,Commonwealth Bank™".encode()
        test_date = date(2024, 1, 15)

        records = parse_csv_content(content, test_date)

        assert len(records) == 1
        assert "™" in records[0]["company_name"]

    def test_parse_large_csv(self):
        """Test parsing large CSV content."""
        # Create a large CSV with many rows
        header = "Product,Short Qty,Issued Qty\n"
        rows = "\n".join([f"STOCK{i},{i * 1000},{i * 100000}" for i in range(1000)])
        content = (header + rows).encode("utf-8")
        test_date = date(2024, 1, 15)

        records = parse_csv_content(content, test_date)

        assert len(records) == 1000
        assert records[0]["asx_code"] == "STOCK0"
        assert records[999]["asx_code"] == "STOCK999"


class TestValidateRecords:
    """Test record validation functionality."""

    def test_validate_basic_records(self):
        """Test validating basic records."""
        records = [
            {
                "asx_code": "CBA",
                "short_sold": 1000,
                "issued_shares": 100000,
                "percent_short": 1.0,
            },
            {
                "asx_code": "ANZ",
                "short_sold": 2000,
                "issued_shares": 200000,
                "percent_short": 1.0,
            },
        ]
        test_date = date(2024, 1, 15)

        validated = validate_records(records, test_date)

        assert len(validated) == 2
        assert validated[0]["asx_code"] == "CBA"
        assert validated[0]["short_sold"] == 1000
        assert validated[1]["asx_code"] == "ANZ"

    def test_validate_with_company_name(self):
        """Test validating records with company names."""
        records = [
            {
                "asx_code": "CBA",
                "company_name": "Commonwealth Bank",
                "short_sold": 1000,
                "issued_shares": 100000,
            }
        ]
        test_date = date(2024, 1, 15)

        validated = validate_records(records, test_date)

        assert len(validated) == 1
        assert validated[0]["company_name"] == "Commonwealth Bank"

    def test_validate_with_percentage(self):
        """Test validating records with percentage values."""
        records = [
            {
                "asx_code": "CBA",
                "short_sold": 1000,
                "issued_shares": 100000,
                "percent_short": 1.0,
            }
        ]
        test_date = date(2024, 1, 15)

        validated = validate_records(records, test_date)

        assert len(validated) == 1
        assert validated[0]["percent_short"] == 1.0

    def test_validate_empty_records(self):
        """Test validating empty records list."""
        records = []
        test_date = date(2024, 1, 15)

        validated = validate_records(records, test_date)
        assert validated == []

    def test_validate_missing_required_fields(self):
        """Test validating records missing required fields."""
        records = [
            {"short_sold": 1000},  # Missing asx_code
            {"asx_code": ""},  # Empty asx_code
            {},  # Empty record
        ]
        test_date = date(2024, 1, 15)

        validated = validate_records(records, test_date)

        # Should filter out invalid records
        assert len(validated) == 0

    def test_validate_with_invalid_numbers(self):
        """Test validating records with invalid numeric values."""
        records = [
            {"asx_code": "CBA", "short_sold": "invalid", "issued_shares": 100000},
            {"asx_code": "ANZ", "short_sold": 1000, "issued_shares": "invalid"},
        ]
        test_date = date(2024, 1, 15)

        validated = validate_records(records, test_date)

        # Should still include records
        assert len(validated) == 2
        assert validated[0]["asx_code"] == "CBA"
        assert validated[1]["asx_code"] == "ANZ"

    def test_validate_zero_division(self):
        """Test validating records with extreme percentage values."""
        records = [
            {
                "asx_code": "CBA",
                "short_sold": 1000,
                "issued_shares": 0,
                "percent_short": 2000.0,
            }
        ]
        test_date = date(2024, 1, 15)

        validated = validate_records(records, test_date)

        assert len(validated) == 1
        assert validated[0]["percent_short"] == 1000.0  # Should clamp to max 1000%

    def test_validate_percentage_clamping(self):
        """Test percentage value clamping."""
        records = [
            {"asx_code": "CBA", "percent_short": -5.0},  # Negative percentage
            {"asx_code": "ANZ", "percent_short": 1500.0},  # Very high percentage
        ]
        test_date = date(2024, 1, 15)

        validated = validate_records(records, test_date)

        assert len(validated) == 2
        assert validated[0]["percent_short"] == 0.0  # Clamped to 0
        assert validated[1]["percent_short"] == 1000.0  # Clamped to 1000

    def test_validate_large_dataset(self):
        """Test validating large dataset."""
        # Create large dataset
        records = []
        for i in range(1000):
            records.append(
                {
                    "asx_code": f"STOCK{i}",
                    "short_sold": i * 1000,
                    "issued_shares": i * 100000,
                }
            )

        test_date = date(2024, 1, 15)

        validated = validate_records(records, test_date)

        assert len(validated) == 1000
        assert validated[0]["asx_code"] == "STOCK0"
        assert validated[999]["asx_code"] == "STOCK999"

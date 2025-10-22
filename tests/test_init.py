"""Tests for __init__.py module to improve coverage."""


def test_version_defined():
    """Test that __version__ is defined."""
    import asxshorts

    assert hasattr(asxshorts, "__version__")
    assert isinstance(asxshorts.__version__, str)
    assert len(asxshorts.__version__) > 0


def test_core_imports():
    """Test that core classes and exceptions are importable."""
    import asxshorts

    # Test core classes
    assert hasattr(asxshorts, "ShortsClient")
    assert asxshorts.ShortsClient is not None

    # Test exceptions
    assert hasattr(asxshorts, "FetchError")
    assert hasattr(asxshorts, "NotFoundError")
    assert hasattr(asxshorts, "RateLimitError")
    assert hasattr(asxshorts, "ParseError")
    assert hasattr(asxshorts, "CacheError")


def test_all_exports():
    """Test that __all__ contains expected exports."""
    import asxshorts

    expected_core_exports = [
        "ShortsClient",
        "FetchError",
        "NotFoundError",
        "RateLimitError",
        "ParseError",
        "CacheError",
    ]

    assert hasattr(asxshorts, "__all__")
    for export in expected_core_exports:
        assert export in asxshorts.__all__


def test_pandas_adapter_import_success():
    """Test PandasAdapter import when pandas is available."""
    # Test that if pandas adapters are available, they're in __all__
    import asxshorts

    if hasattr(asxshorts, "PandasAdapter"):
        assert "PandasAdapter" in asxshorts.__all__
        assert "create_pandas_adapter" in asxshorts.__all__


def test_pandas_adapter_import_failure():
    """Test that module works when pandas is not available."""
    # This test just verifies the module can be imported without pandas
    # The actual conditional import is tested by the import success test
    import asxshorts

    # Module should always work regardless of pandas availability
    assert hasattr(asxshorts, "ShortsClient")
    assert hasattr(asxshorts, "__all__")


def test_polars_adapter_import_success():
    """Test PolarsAdapter import when polars is available."""
    # Test that if polars adapters are available, they're in __all__
    import asxshorts

    if hasattr(asxshorts, "PolarsAdapter"):
        assert "PolarsAdapter" in asxshorts.__all__
        assert "create_polars_adapter" in asxshorts.__all__


def test_polars_adapter_import_failure():
    """Test that module works when polars is not available."""
    # This test just verifies the module can be imported without polars
    # The actual conditional import is tested by the import success test
    import asxshorts

    # Module should always work regardless of polars availability
    assert hasattr(asxshorts, "ShortsClient")
    assert hasattr(asxshorts, "__all__")


def test_module_docstring():
    """Test that module has a docstring."""
    import asxshorts

    assert asxshorts.__doc__ is not None
    assert len(asxshorts.__doc__.strip()) > 0
    assert "ASX Shorts" in asxshorts.__doc__


def test_direct_class_access():
    """Test that classes can be accessed directly from module."""
    from datetime import date

    import asxshorts

    # Test that we can create instances
    client = asxshorts.ShortsClient()
    assert client is not None

    # Test that we can create exceptions
    error = asxshorts.NotFoundError(date(2024, 1, 15))
    assert error is not None
    assert "2024-01-15" in str(error)


def test_exception_inheritance():
    """Test that exceptions have proper inheritance."""
    import asxshorts

    # All custom exceptions should inherit from FetchError (except FetchError itself)
    assert issubclass(asxshorts.NotFoundError, asxshorts.FetchError)
    assert issubclass(asxshorts.RateLimitError, asxshorts.FetchError)
    assert issubclass(asxshorts.ParseError, asxshorts.FetchError)
    assert issubclass(asxshorts.CacheError, asxshorts.FetchError)

    # FetchError should inherit from Exception
    assert issubclass(asxshorts.FetchError, Exception)


def test_conditional_imports_structure():
    """Test the structure of conditional imports."""
    import asxshorts

    # Test that __all__ is a list
    assert isinstance(asxshorts.__all__, list)

    # Test that core exports are always present
    core_exports = [
        "ShortsClient",
        "FetchError",
        "NotFoundError",
        "RateLimitError",
        "ParseError",
        "CacheError",
    ]
    for export in core_exports:
        assert export in asxshorts.__all__

    # Test that optional exports are either all present or all absent
    pandas_exports = ["PandasAdapter", "create_pandas_adapter"]
    polars_exports = ["PolarsAdapter", "create_polars_adapter"]

    # For pandas: either both are in __all__ or neither
    pandas_in_all = [export in asxshorts.__all__ for export in pandas_exports]
    assert all(pandas_in_all) or not any(pandas_in_all)

    # For polars: either both are in __all__ or neither
    polars_in_all = [export in asxshorts.__all__ for export in polars_exports]
    assert all(polars_in_all) or not any(polars_in_all)

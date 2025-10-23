# Changelog

## [0.1.1] - 2024-01-XX

- Add `http_adapter_retries` configuration flag to control urllib3 HTTPAdapter retry strategy
- Refactor data cleaning logic in adapters module
- Update retry settings default (retries now defaults to 0)
- Improve test coverage for retry settings and adapters
- Enhanced test cases for client edge cases

## [0.1.0] - 2024-01-XX

- Initial release of asxshorts, a lightweight Python client for downloading official ASX short position data with local caching capabilities
- Download daily ASX short position CSV files
- Intelligent caching to minimize API calls
- Command-line interface with rich formatting
- Type-safe data models with Pydantic
- Optional pandas/polars integration
- Comprehensive error handling and logging

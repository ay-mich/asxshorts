# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Default `base_url` now points to `https://download.asic.gov.au` and URL resolution prefers the official ASIC JSON index (with fallback to pattern+HTML heuristics). This significantly improves reliability of locating daily CSVs.
- `ShortsClient` no longer calls `logging.basicConfig` (library no longer reconfigures global logging). The CLI still configures logging.
- README and package docs updated to reflect ASIC-first resolution, correct usage of `FetchResult`/`RangeResult`, and CLI aliases (`range`, `cache stats|clear|cleanup`).
- `AsicResolver` now caches the JSON index in-memory per resolver instance to avoid repeated downloads during range operations.
- `adapters.to_pandas` and `adapters.to_polars` no longer instantiate `ShortsClient`; they perform pure conversions without side effects.
- Examples updated to use model attributes consistently and avoid dict-style access.

### Added

- `CompositeResolver` (ASIC JSON index first, then `DefaultResolver`).
- `AsicResolver` which reads `short-selling-data.json` to build CSV URLs.
- Actual timing metrics in `FetchResult.fetch_time_ms` and `RangeResult.total_fetch_time_ms`.
- DataFrame helpers `to_pandas` and `to_polars` in `asxshorts.adapters`.
- Cache stats now include `oldest_file` and `newest_file`.
- PEP 561 typing marker `py.typed` included in distributions.

### Removed

- Unused duplicate package stub at `src/asxshorts/`.
- Unused internal cache helper function.

### Notes

- Requires Python 3.11+ (matches tooling and types).

## [0.1.0] - 2024-01-XX

### Added

- Initial release

### Changed

- N/A

### Deprecated

- N/A

### Removed

- N/A

### Fixed

- N/A

### Security

- N/A

---

## Release Notes

### Version 0.1.0

This is the initial release of asxshorts, a lightweight Python client for downloading official ASX short position data with local caching capabilities.

**Key Features:**

- Download daily ASX short position CSV files
- Intelligent caching to minimize API calls
- Command-line interface with rich formatting
- Type-safe data models with Pydantic
- Optional pandas/polars integration
- Comprehensive error handling and logging

**Getting Started:**

```bash
pip install asxshorts
asxshorts fetch --date 2024-01-15
```

**For Developers:**

```bash
pip install asxshorts[dev]
pre-commit install
pytest
```

See the [README](README.md) for detailed usage instructions and examples.

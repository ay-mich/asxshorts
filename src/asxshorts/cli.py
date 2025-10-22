"""Command-line interface for asxshorts."""

import json
import logging
import traceback
from datetime import date, timedelta
from importlib.metadata import version as get_version
from pathlib import Path

import typer
from dateutil.parser import parse as parse_date

from .client import ShortsClient
from .errors import FetchError, NotFoundError
from .models import ClientSettings


def _within_publish_lag(d: date, lag_days: int) -> bool:
    today = date.today()
    return d >= (today - timedelta(days=lag_days)) and d <= today


def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5


app = typer.Typer(
    name="asxshorts",
    help="Fetch ASX short selling data with local caching",
    no_args_is_help=True,
)

# Sub-app for cache commands (kept in addition to standalone commands)
cache_app = typer.Typer(name="cache", help="Cache management commands")
app.add_typer(cache_app, name="cache")


# Global options
def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@app.command()
def fetch(
    date_str: str = typer.Argument(
        ..., help="Date to fetch (YYYY-MM-DD format, or 'today', 'yesterday')"
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path (JSON format)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force refresh, bypass cache"
    ),
    cache_dir: str | None = typer.Option(
        None, "--cache-dir", help="Custom cache directory"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
) -> None:
    """Fetch short selling data for a specific date."""
    setup_logging(verbose)

    # Parse date
    try:
        if date_str.lower() == "today":
            target_date = date.today()
        elif date_str.lower() == "yesterday":
            target_date = date.today() - timedelta(days=1)
        else:
            target_date = parse_date(date_str).date()
    except ValueError as e:
        typer.echo(f"Error: Invalid date format '{date_str}': {e}", err=True)
        raise typer.Exit(1) from e

    # Create client
    settings = ClientSettings(cache_dir=cache_dir) if cache_dir else ClientSettings()
    client = ShortsClient(settings=settings)

    try:
        # Fetch data
        typer.echo(f"Fetching data for {target_date}...")
        result = client.fetch_day(target_date, force=force)

        cache_status = " (cached)" if result.from_cache else ""
        typer.echo(
            f"✓ Found {result.record_count} records for {target_date}{cache_status}"
        )

        # Convert to JSON-serializable format
        output_data = {
            "date": target_date.isoformat(),
            "record_count": result.record_count,
            "from_cache": result.from_cache,
            "records": [record.model_dump() for record in result.records],
        }

        # Output results
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w") as f:
                json.dump(output_data, f, indent=2, default=str)
            typer.echo(f"✓ Saved to {output}")
        else:
            # Print to stdout
            print(json.dumps(output_data, indent=2, default=str))

    except NotFoundError as e:
        typer.echo(f"✗ No data found for {target_date}", err=True)
        # Provide helpful context for recent dates or weekends
        if _within_publish_lag(target_date, client.settings.publish_lag_days):
            typer.echo(
                "Note: ASIC typically publishes short-selling data with a 5 - 7 day lag.",
                err=True,
            )
        elif _is_weekend(target_date):
            typer.echo("Note: Data is generally not published on weekends.", err=True)
        raise typer.Exit(1) from e
    except FetchError as e:
        typer.echo(f"✗ Fetch failed: {e}", err=True)
        raise typer.Exit(1) from e
    except Exception as e:
        typer.echo(f"✗ Unexpected error: {e}", err=True)
        if verbose:
            traceback.print_exc()
        raise typer.Exit(1) from e


@app.command()
def fetch_range(
    start_date: str = typer.Argument(..., help="Start date (YYYY-MM-DD format)"),
    end_date: str = typer.Argument(..., help="End date (YYYY-MM-DD format)"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path (JSON format)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force refresh, bypass cache"
    ),
    cache_dir: str | None = typer.Option(
        None, "--cache-dir", help="Custom cache directory"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
) -> None:
    """Fetch short selling data for a date range."""
    setup_logging(verbose)

    # Parse dates
    try:
        start = parse_date(start_date).date()
        end = parse_date(end_date).date()
    except ValueError as e:
        typer.echo(f"Error: Invalid date format: {e}", err=True)
        raise typer.Exit(1) from e

    if start > end:
        typer.echo("Error: Start date must be <= end date", err=True)
        raise typer.Exit(1)

    # Create client
    settings = ClientSettings(cache_dir=cache_dir) if cache_dir else ClientSettings()
    client = ShortsClient(settings=settings)

    try:
        # Fetch data
        typer.echo(f"Fetching data from {start} to {end}...")
        result = client.fetch_range(start, end, force=force)

        typer.echo(
            f"✓ Found {result.total_records} total records across {result.successful_dates} dates"
        )
        if result.failed_dates:
            typer.echo(
                f"⚠ Failed to fetch data for {len(result.failed_dates)} dates: {result.failed_dates}"
            )
            # Summarize likely reasons for missing dates
            lag_dates = [
                d
                for d in result.failed_dates
                if _within_publish_lag(d, client.settings.publish_lag_days)
            ]
            weekend_dates = [d for d in result.failed_dates if _is_weekend(d)]
            if lag_dates:
                typer.echo(
                    f"Note: {len(lag_dates)} date(s) fall within ASIC's typical 5 - 7 day publish lag.",
                )
            if weekend_dates:
                typer.echo(
                    f"Note: {len(weekend_dates)} date(s) are weekends; data may not be published.",
                )

        # Convert to JSON-serializable format
        all_records = []
        for date, fetch_result in result.results.items():
            for record in fetch_result.records:
                record_dict = record.model_dump()
                record_dict["date"] = date.isoformat()
                all_records.append(record_dict)

        output_data = {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total_records": result.total_records,
            "successful_dates": [d.isoformat() for d in result.successful_dates],
            "failed_dates": [d.isoformat() for d in result.failed_dates],
            "records": all_records,
        }

        # Output results
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w") as f:
                json.dump(output_data, f, indent=2, default=str)
            typer.echo(f"✓ Saved to {output}")
        else:
            # Print to stdout
            print(json.dumps(output_data, indent=2, default=str))

    except FetchError as e:
        typer.echo(f"✗ Fetch failed: {e}", err=True)
        raise typer.Exit(1) from e
    except Exception as e:
        typer.echo(f"✗ Unexpected error: {e}", err=True)
        if verbose:
            traceback.print_exc()
        raise typer.Exit(1) from e


# Provide alias 'range' to match README examples
@app.command(name="range")
def range_alias(
    start_date: str,
    end_date: str,
    output: Path | None = typer.Option(None, "--output", "-o"),
    force: bool = typer.Option(False, "--force", "-f"),
    cache_dir: str | None = typer.Option(None, "--cache-dir"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Alias for fetch-range for compatibility with README."""
    fetch_range(
        start_date=start_date,
        end_date=end_date,
        output=output,
        force=force,
        cache_dir=cache_dir,
        verbose=verbose,
    )


@app.command()
def cache_info(
    cache_dir: str | None = typer.Option(
        None, "--cache-dir", help="Custom cache directory"
    ),
) -> None:
    """Show cache statistics."""
    settings = ClientSettings(cache_dir=cache_dir) if cache_dir else ClientSettings()
    client = ShortsClient(settings=settings)
    stats = client.cache_stats()

    typer.echo("Cache Statistics:")
    typer.echo(f"  Path: {stats.path}")
    typer.echo(f"  Files: {stats.count}")
    typer.echo(
        f"  Size: {stats.size_bytes:,} bytes ({stats.size_bytes / 1024 / 1024:.1f} MB)"
    )


# Add as subcommand: cache stats
@cache_app.command(name="stats")
def cache_stats_cmd(cache_dir: str | None = typer.Option(None, "--cache-dir")) -> None:
    """Show cache statistics (alias)."""
    cache_info(cache_dir=cache_dir)


@app.command()
def clear_cache(
    cache_dir: str | None = typer.Option(
        None, "--cache-dir", help="Custom cache directory"
    ),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Clear all cached files."""
    settings = ClientSettings(cache_dir=cache_dir) if cache_dir else ClientSettings()
    client = ShortsClient(settings=settings)
    stats = client.cache_stats()

    if stats.count == 0:
        typer.echo("Cache is already empty")
        return

    if not confirm:
        proceed = typer.confirm(
            f"Clear {stats.count} cached files ({stats.size_bytes / 1024 / 1024:.1f} MB)?"
        )
        if not proceed:
            typer.echo("Cancelled")
            return

    client.clear_cache()
    typer.echo("✓ Cache cleared")


# Add as subcommand: cache clear
@cache_app.command(name="clear")
def cache_clear_cmd(
    cache_dir: str | None = typer.Option(None, "--cache-dir"),
    confirm: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Clear all cached files (alias)."""
    clear_cache(cache_dir=cache_dir, confirm=confirm)


@app.command()
def cleanup_cache(
    max_age_days: int = typer.Option(
        30, "--max-age", help="Remove files older than this many days"
    ),
    cache_dir: str | None = typer.Option(
        None, "--cache-dir", help="Custom cache directory"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
) -> None:
    """Remove old cached files."""
    setup_logging(verbose)

    settings = ClientSettings(cache_dir=cache_dir) if cache_dir else ClientSettings()
    client = ShortsClient(settings=settings)
    client.cleanup_cache(max_age_days)
    typer.echo(f"✓ Cleaned up cache files older than {max_age_days} days")


# Add as subcommand: cache cleanup
@cache_app.command(name="cleanup")
def cache_cleanup_cmd(
    max_age_days: int = typer.Option(30, "--max-age"),
    cache_dir: str | None = typer.Option(None, "--cache-dir"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Remove old cached files (alias)."""
    cleanup_cache(max_age_days=max_age_days, cache_dir=cache_dir, verbose=verbose)


@app.command()
def version() -> None:
    """Show version information."""
    try:
        pkg_version = get_version("asxshorts")
    except Exception:
        pkg_version = "unknown"

    typer.echo(f"asxshorts {pkg_version}")


def main() -> None:
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()

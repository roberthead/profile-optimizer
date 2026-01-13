"""
Data normalization utilities for cleaning and transforming member data.

These functions are used when importing member data from various sources
(JSON files, API responses) to ensure consistent data format in the database.
"""

from datetime import datetime
from typing import Any


def normalize_string(value: str | None) -> str | None:
    """
    Convert empty strings to None for cleaner data storage.

    Args:
        value: The string value to normalize, or None.

    Returns:
        The stripped string if non-empty, otherwise None.

    Examples:
        >>> normalize_string("  hello  ")
        'hello'
        >>> normalize_string("")
        None
        >>> normalize_string("   ")
        None
        >>> normalize_string(None)
        None
    """
    if value is None or value.strip() == "":
        return None
    return value.strip()


def normalize_list(value: list[Any] | None) -> list[Any]:
    """
    Ensure list is not None and filter out empty/whitespace-only strings.

    Args:
        value: The list to normalize, or None.

    Returns:
        A list with empty strings removed. Returns empty list if input is None.

    Examples:
        >>> normalize_list(["a", "", "b", "  ", "c"])
        ['a', 'b', 'c']
        >>> normalize_list(None)
        []
        >>> normalize_list([])
        []
    """
    if not value:
        return []
    return [item for item in value if item and str(item).strip()]


def parse_datetime(dt_string: str | None) -> datetime | None:
    """
    Parse datetime string from JSON export format.

    Handles the format used in White Rabbit data exports:
    "2025-11-27 06:08:44.635426" (space separator instead of T)

    Args:
        dt_string: The datetime string to parse, or None.

    Returns:
        A datetime object if parsing succeeds, otherwise None.

    Examples:
        >>> parse_datetime("2025-11-27 06:08:44.635426")
        datetime.datetime(2025, 11, 27, 6, 8, 44, 635426)
        >>> parse_datetime("2025-11-27T06:08:44.635426")
        datetime.datetime(2025, 11, 27, 6, 8, 44, 635426)
        >>> parse_datetime(None)
        None
        >>> parse_datetime("invalid")
        None
    """
    if not dt_string:
        return None
    try:
        # Handle format: "2025-11-27 06:08:44.635426"
        # Also works with ISO format: "2025-11-27T06:08:44.635426"
        return datetime.fromisoformat(dt_string.replace(" ", "T"))
    except ValueError:
        return None

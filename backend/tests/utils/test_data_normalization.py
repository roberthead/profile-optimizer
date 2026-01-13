"""Tests for data normalization utilities."""

from datetime import datetime

import pytest

from app.utils import normalize_string, normalize_list, parse_datetime


class TestNormalizeString:
    """Tests for normalize_string function."""

    def test_strips_whitespace(self):
        assert normalize_string("  hello  ") == "hello"
        assert normalize_string("\thello\n") == "hello"

    def test_returns_none_for_empty_string(self):
        assert normalize_string("") is None

    def test_returns_none_for_whitespace_only(self):
        assert normalize_string("   ") is None
        assert normalize_string("\t\n") is None

    def test_returns_none_for_none(self):
        assert normalize_string(None) is None

    def test_preserves_non_empty_string(self):
        assert normalize_string("hello") == "hello"
        assert normalize_string("hello world") == "hello world"


class TestNormalizeList:
    """Tests for normalize_list function."""

    def test_filters_empty_strings(self):
        assert normalize_list(["a", "", "b"]) == ["a", "b"]

    def test_filters_whitespace_strings(self):
        assert normalize_list(["a", "   ", "b"]) == ["a", "b"]

    def test_returns_empty_list_for_none(self):
        assert normalize_list(None) == []

    def test_returns_empty_list_for_empty_list(self):
        assert normalize_list([]) == []

    def test_preserves_non_empty_items(self):
        assert normalize_list(["a", "b", "c"]) == ["a", "b", "c"]

    def test_handles_mixed_types(self):
        # Items are converted to string for the strip check
        result = normalize_list([1, "a", None, "b", 0])
        # None and empty items are filtered, but 0 and 1 are kept
        assert result == [1, "a", "b"]

    def test_handles_all_empty_items(self):
        assert normalize_list(["", "   ", None]) == []


class TestParseDatetime:
    """Tests for parse_datetime function."""

    def test_parses_space_separated_format(self):
        result = parse_datetime("2025-11-27 06:08:44.635426")
        expected = datetime(2025, 11, 27, 6, 8, 44, 635426)
        assert result == expected

    def test_parses_iso_format(self):
        result = parse_datetime("2025-11-27T06:08:44.635426")
        expected = datetime(2025, 11, 27, 6, 8, 44, 635426)
        assert result == expected

    def test_parses_without_microseconds(self):
        result = parse_datetime("2025-11-27 06:08:44")
        expected = datetime(2025, 11, 27, 6, 8, 44)
        assert result == expected

    def test_returns_none_for_none(self):
        assert parse_datetime(None) is None

    def test_returns_none_for_empty_string(self):
        assert parse_datetime("") is None

    def test_returns_none_for_invalid_format(self):
        assert parse_datetime("invalid") is None
        assert parse_datetime("2025/11/27") is None
        assert parse_datetime("not-a-date") is None

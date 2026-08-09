from __future__ import annotations

from src.parsing.dates import days_between, parse_date


def test_date_formats() -> None:
    assert parse_date("10 March 2021") == "2021-03-10"
    assert parse_date("March 10, 2021") == "2021-03-10"
    assert parse_date("2021-03-10") == "2021-03-10"
    assert parse_date("10/03/2021") == "2021-03-10"
    assert parse_date("10-03-2021") == "2021-03-10"


def test_elapsed_days() -> None:
    assert days_between("2021-03-10", "2025-06-26") == 1569


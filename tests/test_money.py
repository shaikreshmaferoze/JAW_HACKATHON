from __future__ import annotations

from src.parsing.money import parse_money, parse_money_threshold


def test_money_crore_variants() -> None:
    assert parse_money("INR 33.38 Cr") == 333800000
    assert parse_money("Rs. 33.38 Cr") == 333800000
    assert parse_money("₹33.38 crore") == 333800000
    assert parse_money("33.38 Cr") == 333800000


def test_money_lakh_variants() -> None:
    assert parse_money("3,338.00 Lakh") == 333800000
    assert parse_money("3338 Lakh") == 333800000


def test_money_indian_grouping_and_plain() -> None:
    assert parse_money("33,38,00,000") == 333800000
    assert parse_money("333800000") == 333800000
    assert parse_money("INR 33,38,00,000/-") == 333800000


def test_word_thresholds() -> None:
    assert parse_money_threshold("INR 20 Cr") == 200000000
    assert parse_money_threshold("seventy-three crore mark") == 730000000
    assert parse_money_threshold("six crore line") == 60000000


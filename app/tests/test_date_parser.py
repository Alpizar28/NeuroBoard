from datetime import date

from app.services.date_parser_service import parse_due_date


def test_parse_manana_from_costa_rica_reference() -> None:
    parsed = parse_due_date("mañana", base_date=date(2026, 2, 27))
    assert parsed == date(2026, 2, 28)


def test_parse_next_weekday() -> None:
    parsed = parse_due_date("viernes", base_date=date(2026, 2, 27))
    assert parsed == date(2026, 3, 6)


def test_parse_numeric_rolls_to_next_year_when_needed() -> None:
    parsed = parse_due_date("15/01", base_date=date(2026, 2, 27))
    assert parsed == date(2027, 1, 15)


def test_invalid_numeric_date_returns_none() -> None:
    parsed = parse_due_date("31/02", base_date=date(2026, 2, 27))
    assert parsed is None

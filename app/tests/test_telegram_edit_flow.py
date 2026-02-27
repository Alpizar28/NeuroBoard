from app.services.telegram_service import parse_edit_command


def test_parses_edit_command_with_lines() -> None:
    parsed = parse_edit_command("/edit 12\n-Lavar ropa\n-Comprar cafe")
    assert parsed == (12, ["-Lavar ropa", "-Comprar cafe"])


def test_rejects_edit_command_without_numeric_id() -> None:
    assert parse_edit_command("/edit abc\n-Lavar ropa") is None


def test_rejects_non_edit_message() -> None:
    assert parse_edit_command("hola mundo") is None

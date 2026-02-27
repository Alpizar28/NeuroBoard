from app.services.telegram_service import build_preview_reply_markup, parse_preview_callback


def test_builds_inline_keyboard_with_preview_id() -> None:
    markup = build_preview_reply_markup(7)
    assert markup["inline_keyboard"][0][0]["callback_data"] == "preview:confirm:7"
    assert markup["inline_keyboard"][0][1]["callback_data"] == "preview:edit:7"
    assert markup["inline_keyboard"][0][2]["callback_data"] == "preview:cancel:7"


def test_parses_valid_preview_callback() -> None:
    parsed = parse_preview_callback("preview:confirm:9")
    assert parsed == ("confirm", 9)


def test_rejects_invalid_preview_callback() -> None:
    assert parse_preview_callback("bad:data") is None

from app.services.telegram_service import (
    build_answer_callback_call,
    build_edit_message_call,
    build_send_message_call,
    extract_chat_id,
    extract_message_id,
)


def test_builds_send_message_payload() -> None:
    payload = build_send_message_call(123, "hello")
    assert payload["method"] == "sendMessage"
    assert payload["chat_id"] == 123
    assert payload["text"] == "hello"


def test_builds_edit_message_payload() -> None:
    payload = build_edit_message_call(123, 77, "updated")
    assert payload["method"] == "editMessageText"
    assert payload["message_id"] == 77


def test_builds_answer_callback_payload() -> None:
    payload = build_answer_callback_call("cb1", "done")
    assert payload["method"] == "answerCallbackQuery"
    assert payload["callback_query_id"] == "cb1"


def test_extracts_chat_and_message_ids() -> None:
    message = {"chat": {"id": 555}, "message_id": 42}
    assert extract_chat_id(message) == 555
    assert extract_message_id(message) == 42

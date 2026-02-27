from app.services.telegram_service import extract_caption_lines, extract_photo_file_id


def test_extracts_largest_photo_file_id() -> None:
    file_id = extract_photo_file_id(
        {
            "photo": [
                {"file_id": "small", "file_size": 100},
                {"file_id": "large", "file_size": 300},
            ]
        }
    )
    assert file_id == "large"


def test_returns_none_when_no_photo_is_present() -> None:
    assert extract_photo_file_id({"text": "hola"}) is None


def test_extracts_non_empty_caption_lines() -> None:
    lines = extract_caption_lines({"caption": "-Lavar ropa\n\n-Comprar cafe"})
    assert lines == ["-Lavar ropa", "-Comprar cafe"]

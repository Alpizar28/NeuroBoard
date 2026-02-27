from datetime import date

from app.services.vision_service import parse_vision_payload


def test_parses_valid_vision_payload() -> None:
    tasks, global_confidence = parse_vision_payload(
        {
            "tasks": [
                {
                    "text": "JOKEM OS: Fix deploy issue",
                    "category_hint": "Jokem",
                    "due_text": "mañana",
                    "subtasks": ["restart api"],
                    "confidence": 0.93,
                    "warnings": [],
                }
            ],
            "global_confidence": 0.81,
        },
        base_date=date(2026, 2, 27),
    )

    assert global_confidence == 0.81
    assert len(tasks) == 1
    assert tasks[0].list_name == "Jokem"
    assert tasks[0].due_date == date(2026, 2, 28)
    assert tasks[0].subtasks == ["restart api"]


def test_invalid_category_hint_falls_back_to_classifier() -> None:
    tasks, _ = parse_vision_payload(
        {
            "tasks": [
                {
                    "text": "JP: Rutina gym mañana",
                    "category_hint": "Unknown",
                    "confidence": 0.6,
                }
            ],
            "global_confidence": 0.6,
        },
        base_date=date(2026, 2, 27),
    )

    assert tasks[0].list_name == "Personales"


def test_invalid_due_iso_adds_warning() -> None:
    tasks, _ = parse_vision_payload(
        {
            "tasks": [
                {
                    "text": "Lavar ropa",
                    "due_iso": "2026-02-31",
                    "confidence": 0.5,
                }
            ],
            "global_confidence": 0.5,
        }
    )

    assert "invalid due_iso" in tasks[0].warnings[0]

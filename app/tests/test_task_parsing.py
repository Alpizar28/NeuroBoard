from datetime import date

from app.services.task_parsing_service import build_preview_from_lines


def test_groups_subtasks_under_previous_main_task() -> None:
    tasks = build_preview_from_lines(
        [
            "-SUPERIOR: Exam viernes",
            "• tema 1",
            "• tema 2",
            "-Lavar ropa",
        ]
    )

    assert len(tasks) == 2
    assert tasks[0].subtasks == ["tema 1", "tema 2"]
    assert tasks[1].subtasks == []


def test_assigns_due_dates_and_categories() -> None:
    tasks = build_preview_from_lines(
        ["-JP: Rutina gym mañana"],
        base_date=date(2026, 2, 27),
    )

    assert len(tasks) == 1
    assert tasks[0].list_name == "Personales"
    assert tasks[0].due_date == date(2026, 2, 28)


def test_ignores_orphan_subtasks() -> None:
    tasks = build_preview_from_lines(["• sin padre", "-Lavar ropa"])
    assert len(tasks) == 1
    assert tasks[0].text == "Lavar ropa"

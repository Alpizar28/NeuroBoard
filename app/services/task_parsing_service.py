from __future__ import annotations

from datetime import date
from typing import Iterable

from app.models.schemas import ParsedTask
from app.services.classification_service import classify_task
from app.services.date_parser_service import parse_due_date


DATE_MARKERS = (
    " hoy",
    " manana",
    " mañana",
    " pasado manana",
    " pasado mañana",
    " la otra semana",
    " lunes",
    " martes",
    " miercoles",
    " miércoles",
    " jueves",
    " viernes",
    " sabado",
    " sábado",
    " domingo",
)


def _extract_due_text(text: str) -> tuple[str, str | None]:
    lowered = f" {text.lower()}"
    for marker in DATE_MARKERS:
        idx = lowered.find(marker)
        if idx != -1:
            actual_idx = idx - 1
            prefix = text[:actual_idx].strip(" -")
            due_text = text[actual_idx:].strip()
            return prefix, due_text
    return text.strip(" -"), None


def build_preview_from_lines(
    lines: Iterable[str],
    *,
    base_date: date | None = None,
) -> list[ParsedTask]:
    tasks: list[ParsedTask] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("•"):
            if tasks:
                tasks[-1].subtasks.append(line.lstrip("•").strip())
            elif tasks == []:
                continue
            continue

        task_text, due_text = _extract_due_text(line)
        classification = classify_task(task_text)
        due_date = parse_due_date(due_text, base_date=base_date)
        warnings: list[str] = []
        if due_text and due_date is None:
            warnings.append("Due date text could not be parsed.")

        tasks.append(
            ParsedTask(
                text=task_text,
                raw_text=raw_line,
                list_name=classification.list_name,
                confidence=classification.confidence,
                classification_reason=classification.reason,
                due_text=due_text,
                due_date=due_date,
                warnings=warnings,
            )
        )

    return tasks

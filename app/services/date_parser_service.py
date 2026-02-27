from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


WEEKDAYS = {
    "lunes": 0,
    "lun": 0,
    "martes": 1,
    "mar": 1,
    "miercoles": 2,
    "miércoles": 2,
    "mie": 2,
    "mié": 2,
    "jueves": 3,
    "jue": 3,
    "viernes": 4,
    "vie": 4,
    "sabado": 5,
    "sábado": 5,
    "sab": 5,
    "sábado.": 5,
    "domingo": 6,
    "dom": 6,
}


def _resolve_next_weekday(base_date: date, target_weekday: int) -> date:
    days_ahead = (target_weekday - base_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return base_date + timedelta(days=days_ahead)


def parse_due_date(
    due_text: str | None,
    *,
    base_date: date | None = None,
    timezone_name: str = "America/Costa_Rica",
) -> date | None:
    if not due_text:
        return None

    tz = ZoneInfo(timezone_name)
    reference_date = base_date or datetime.now(tz).date()
    normalized = due_text.strip().lower()

    if not normalized:
        return None

    if "pasado manana" in normalized or "pasado mañana" in normalized:
        return reference_date + timedelta(days=2)
    if normalized == "hoy":
        return reference_date
    if normalized == "manana" or normalized == "mañana":
        return reference_date + timedelta(days=1)
    if "la otra semana" in normalized:
        return reference_date + timedelta(days=7)

    if normalized in WEEKDAYS:
        return _resolve_next_weekday(reference_date, WEEKDAYS[normalized])

    match = re.search(r"\b(\d{1,2})[/-](\d{1,2})\b", normalized)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = reference_date.year
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None

        if candidate < reference_date:
            try:
                candidate = date(year + 1, month, day)
            except ValueError:
                return None
        return candidate

    return None

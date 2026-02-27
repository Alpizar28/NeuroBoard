from __future__ import annotations

from dataclasses import dataclass


COURSE_PREFIXES = {"SUPERIOR", "ELEMENTOS", "CA"}
PROJECT_PREFIXES = {"JOKEM OS", "LA FENICE", "GYM TAMARINDO"}
PERSONAL_PREFIX = "JP"


@dataclass(frozen=True)
class ClassificationResult:
    list_name: str
    confidence: float
    reason: str


def classify_task(task_text: str) -> ClassificationResult:
    normalized = task_text.strip()
    if not normalized:
        return ClassificationResult(
            list_name="Domesticas",
            confidence=0.0,
            reason="Empty task text.",
        )

    prefix, has_colon, remainder = normalized.partition(":")
    normalized_prefix = prefix.strip().upper()
    has_payload = bool(remainder.strip())

    if has_colon and normalized_prefix in COURSE_PREFIXES:
        return ClassificationResult(
            list_name="Proyectos",
            confidence=0.98 if has_payload else 0.7,
            reason=f"Matched course prefix '{normalized_prefix}:'.",
        )

    if has_colon and normalized_prefix in PROJECT_PREFIXES:
        return ClassificationResult(
            list_name="Jokem",
            confidence=0.98 if has_payload else 0.7,
            reason=f"Matched project prefix '{normalized_prefix}:'.",
        )

    if has_colon and normalized_prefix == PERSONAL_PREFIX:
        return ClassificationResult(
            list_name="Personales",
            confidence=0.98 if has_payload else 0.7,
            reason="Matched personal prefix 'JP:'.",
        )

    if has_colon:
        return ClassificationResult(
            list_name="Domesticas",
            confidence=0.45,
            reason=f"Unknown prefix '{normalized_prefix}:', falling back to Domesticas.",
        )

    return ClassificationResult(
        list_name="Domesticas",
        confidence=0.9,
        reason="No prefix, using Domesticas default.",
    )

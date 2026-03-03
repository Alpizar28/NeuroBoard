"""Centralized constants for NeuroBoard.

Single source of truth for:
- Valid task list names (used by classification, vision, and google tasks services)
- Valid preview status values
"""
from __future__ import annotations

from typing import Literal


# ── Task list names ──────────────────────────────────────────────────────────
LIST_NAMES: frozenset[str] = frozenset({"Proyectos", "Jokem", "Personales", "Domesticas"})

ListName = Literal["Proyectos", "Jokem", "Personales", "Domesticas"]


# ── Preview status values ────────────────────────────────────────────────────
PREVIEW_STATUS_PENDING = "pending"
PREVIEW_STATUS_EDITING = "editing"
PREVIEW_STATUS_CONFIRMED = "confirmed"
PREVIEW_STATUS_COMPLETED = "completed"
PREVIEW_STATUS_CREATION_FAILED = "creation_failed"
PREVIEW_STATUS_CANCELLED = "cancelled"
PREVIEW_STATUS_EXPIRED = "expired"

PREVIEW_ACTIVE_STATUSES: frozenset[str] = frozenset({
    PREVIEW_STATUS_PENDING,
    PREVIEW_STATUS_EDITING,
    PREVIEW_STATUS_CONFIRMED,
    PREVIEW_STATUS_CREATION_FAILED,
})

PreviewStatus = Literal[
    "pending",
    "editing",
    "confirmed",
    "completed",
    "creation_failed",
    "cancelled",
    "expired",
]

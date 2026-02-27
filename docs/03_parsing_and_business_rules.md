# Parsing and Business Rules

## 1. Task Classification Rules
Classification must happen per task.

**Category Mapping:**
- `COURSE_NAME:` → Proyectos (e.g., SUPERIOR, ELEMENTOS, CA)
- `PROJECT_NAME:` → Jokem (e.g., JOKEM OS, LA FENICE, GYM TAMARINDO)
- `JP:` → Personales
- *No prefix* → Domésticas

**Confidence Strategy:**
Even if classification seems correct, ALWAYS show preview and ALWAYS require user confirmation. No auto-creation without confirmation.

## 2. Subtask Parsing Rules
- Line starts with `•` and is indented below previous main task.
- Bullet lines belong to the nearest previous main task.
- No multi-level nesting in v1.
- If structure is ambiguous → mark low confidence.

## 3. Natural Date Interpretation (Costa Rica timezone)
- **Relative:** hoy, mañana, pasado mañana, la otra semana
- **Weekdays:** lunes, martes, viernes, lun, vie
- **Numeric:** 15/03, 15-03

*If ambiguous:* Highlight in preview and allow user correction.

## 4. Duplicate Detection
- Preprocess image -> Generate SHA256 hash -> Store hash in DB.
- If hash exists -> Abort processing and notify user. (Optional: manual override later).

## 5. Low Confidence Handling
If Vision API returns poor structure, missing hierarchy, or low confidence score:
- Reject structured creation.
- Ask user to retake photo.
- Do not create partial tasks.

## 6. Preview UX Requirements
Preview must include tasks grouped by target list, tasks with interpreted date, subtasks visually indented, and an editable structure.
Buttons: `Confirm`, `Edit`, `Cancel`.
No task is created before confirmation.

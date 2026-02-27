# Parsing and Business Rules

## 1. Task Classification Rules
Classification is deterministic and happens per task.

### Active Mapping
- `SUPERIOR:`, `ELEMENTOS:`, `CA:` -> `Proyectos`
- `JOKEM OS:`, `LA FENICE:`, `GYM TAMARINDO:` -> `Jokem`
- `JP:` -> `Personales`
- no prefix -> `Domesticas`
- unknown prefix -> fallback to `Domesticas` with lower confidence

### Important Note
Even if classification is high-confidence, the system still builds a preview first. Nothing should be created before confirmation.

## 2. Subtask Rules
- A line starting with `•` is treated as a subtask.
- A subtask attaches to the nearest previous main task.
- Orphan subtask lines are ignored.
- Current implementation is single-level only.

## 3. Date Parsing Rules
The current parser supports common Spanish inputs, using Costa Rica timezone logic as the intended business context.

### Supported Inputs
- Relative:
  - `hoy`
  - `mañana`
  - `pasado mañana`
  - `la otra semana`
- Weekdays:
  - `lunes`, `martes`, `viernes`, etc.
  - short forms like `lun`, `vie`
- Numeric:
  - `15/03`
  - `15-03`

### Current Behavior
- Weekdays resolve to the next occurrence, not the same day.
- Numeric dates that already passed in the current year roll to next year.
- Invalid dates remain unresolved and generate warnings.

## 4. Vision API Handling
The backend first tries the Vision API for photo-based extraction.

### Current Rules
- The response must match a strict JSON contract.
- The payload is validated with Pydantic before use.
- If the payload is malformed, empty, or too low-confidence, the backend falls back to local text parsing.
- Requests to the Vision API are retried with bounded backoff before failing.
- Allowed `category_hint` values from vision are:
  - `Proyectos`
  - `Jokem`
  - `Personales`
  - `Domesticas`
- Invalid `category_hint` values are ignored and replaced by local deterministic classification.

## 5. Duplicate Detection
- The backend preprocesses the image first.
- It calculates SHA256 from the processed image bytes.
- If the hash already exists in the database, the request is treated as duplicate and no new preview is created.

## 6. Preview Rules
The preview is the center of the workflow.

### Current Behavior
- Every valid parsing path ends in a preview.
- A preview is stored in SQLite before confirmation.
- A preview has a persistent `preview_id`.
- A preview can move through:
  - `pending`
  - `editing`
  - `confirmed`
  - `creation_failed`
  - `completed`
  - `cancelled`
  - `expired`

## 7. Edit Rules
- If the user taps `Edit`, the preview moves to `editing`.
- The user can submit:
  - `/edit <preview_id>`
  - followed by corrected task lines
- The backend replaces the stored preview content in place.
- The same `preview_id` is preserved.

## 8. Confirmation and Creation Rules
- `Confirm` creates tasks in Google Tasks.
- Creation is idempotent per preview and per task index.
- Repeating `Confirm` does not recreate tasks already created.
- Subtasks are created as real child tasks in Google Tasks.
- Google Tasks requests now retry on transient failures.
- If Google returns `401` and refresh credentials are configured, the backend can refresh the access token and retry.

## 9. Expiration Rule
- Old previews are automatically marked `expired`.
- Expiration is based on `PREVIEW_EXPIRATION_MINUTES`.
- Expired previews should not be treated as active work items.

## 10. Current Validation Status
- The implemented parsing and workflow rules are covered by automated tests in `app/tests/`.
- The full current test suite passes inside Docker.

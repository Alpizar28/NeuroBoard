# Database Schema (SQLite) - Current State

## 1. Purpose
SQLite is the single persistence layer for the current MVP.

It currently stores:
- duplicate image fingerprints
- preview state
- idempotency records
- audit logs
- OAuth token placeholder data

## 2. Active Tables

### `images_processed`
Used for duplicate detection.

- `id`
- `hash` (SHA256, unique)
- `timestamp`

### `tasks_created`
Legacy table from the initial schema.

Current note:
- it exists in the model layer
- the active idempotent creation flow currently relies more directly on `preview_task_creations`

Columns:
- `id`
- `google_task_id`
- `parent_id`
- `list_name`
- `timestamp`

### `logs`
Used for lightweight operational audit events.

Columns:
- `id`
- `timestamp`
- `tasks_detected`
- `tasks_created`
- `status`
- `error_message`

Examples of statuses currently used:
- `image_received`
- `duplicate_image`
- `vision_success`
- `vision_failed`
- `preview_ready`
- `preview_edited`
- `preview_confirmed`
- `google_tasks_created`
- `google_tasks_failed`
- `telegram_dispatch_failed`
- `previews_expired`

### `oauth_tokens`
Placeholder table for refresh-token persistence.

Current note:
- the table exists
- the full refresh-token lifecycle is not fully implemented yet

Columns:
- `id`
- `encrypted_refresh_token`
- `timestamp`

### `pending_previews`
Core table for preview workflow state.

Columns:
- `id`
- `image_hash` (nullable)
- `payload_json` (serialized tasks)
- `source` (`vision`, `fallback_text`, `manual_edit`, etc.)
- `status`
- `created_at`
- `updated_at`

This table represents the current active workflow state for each preview.

### `preview_task_creations`
Core idempotency table for Google Tasks creation.

Columns:
- `id`
- `preview_id`
- `task_key` (unique stable key, e.g. parent or subtask slot)
- `google_task_id`
- `list_name`
- `timestamp`

This table prevents duplicate task creation when:
- Telegram retries callbacks
- the user clicks `Confirm` multiple times
- creation partially succeeds and later resumes

## 3. Current Data Model Reality
The database has moved beyond the original design.

The most important tables right now are:
- `images_processed`
- `pending_previews`
- `preview_task_creations`
- `logs`

Those four tables are what make the current backend workflow actually stateful and reliable.

## 4. Current Schema Maturity
The schema is sufficient for the current backend MVP, but likely next schema-level improvements are:
- migrations instead of only `create_all`
- indexes tuned after real traffic
- stronger token storage strategy for Google OAuth refresh flow

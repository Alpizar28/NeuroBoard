# Database Schema (SQLite)

## tables

### `images_processed`
- `id`
- `hash` (SHA256)
- `timestamp`

### `tasks_created`
- `id`
- `google_task_id`
- `parent_id`
- `list_name`
- `timestamp`

### `logs`
- `id`
- `timestamp`
- `tasks_detected`
- `tasks_created`
- `status`
- `error_message`

### `oauth_tokens`
- `encrypted_refresh_token`
- `timestamp`

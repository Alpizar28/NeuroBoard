# NeuroBoard

NeuroBoard is a lightweight FastAPI backend that turns handwritten task input from Telegram into structured Google Tasks entries, with a mandatory preview-and-confirmation step before creation.

## Current Status
The project is currently in an advanced backend MVP stage.

The main workflow is already implemented:
- Telegram webhook reception
- Telegram image download
- image preprocessing
- duplicate image detection with SHA256
- Vision API extraction with strict schema validation
- fallback text parsing when vision fails
- deterministic task classification
- date parsing for common Spanish inputs
- preview persistence in SQLite
- `Confirm`, `Edit`, and `Cancel` flow
- manual correction with `/edit <preview_id>`
- idempotent Google Tasks creation
- real subtask creation in Google Tasks
- automatic preview expiration
- admin preview inspection endpoint
- optional execution of outbound Telegram Bot API calls from the backend
- retries with backoff for Telegram, Vision, and Google integrations
- base support for Google access-token refresh

## Core Flow
1. Telegram sends a webhook.
2. The backend validates the Telegram secret header.
3. If the message contains a photo, the backend downloads and preprocesses it.
4. The processed image is hashed and checked against prior images.
5. The backend tries the Vision API first.
6. If the Vision API fails or returns weak output, the backend falls back to local text parsing.
7. The backend stores a preview in SQLite.
8. The user confirms, edits, or cancels.
9. On confirmation, the backend creates tasks in Google Tasks idempotently.

## Project Structure
- `app/`
  - FastAPI app, services, models, utils, and tests
- `docs/`
  - current project overview, architecture, business rules, and DB schema
- `skills/`
  - internal agent skills aligned to this project
- `Dockerfile`
  - slim Python container
- `docker-compose.yml`
  - local service orchestration

## Main Endpoints
- `POST /api/telegram/webhook`
  - main Telegram webhook entrypoint
- `GET /api/telegram/previews`
  - admin endpoint for preview inspection
  - requires `X-Admin-Api-Token`

## Required Environment Variables
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_SECRET_TOKEN`
- `VISION_API_URL`
- `GOOGLE_TASKS_ACCESS_TOKEN`
- `GOOGLE_TASKS_REFRESH_TOKEN`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_TOKEN_URL`
- `GOOGLE_TASKLIST_PROYECTOS_ID`
- `GOOGLE_TASKLIST_JOKEM_ID`
- `GOOGLE_TASKLIST_PERSONALES_ID`
- `GOOGLE_TASKLIST_DOMESTICAS_ID`
- `PREVIEW_EXPIRATION_MINUTES`
- `ADMIN_API_TOKEN`
- `HTTP_RETRY_ATTEMPTS`
- `HTTP_RETRY_BACKOFF_SECONDS`
- `DATABASE_URL`

See [.env.example](/home/pablo/Jokem/NeuroBoard/.env.example) for the current template.

## Local Run
```bash
uvicorn app.main:app --reload
```

## Testing Note
The repository includes unit tests and HTTP tests under `app/tests/`.

Validation already completed:
```bash
python3 -m compileall app
docker build -t neuroboard-test .
docker run --rm neuroboard-test pytest app/tests
```

Current result:
- `42 passed`

The test suite is fully runnable in Docker even if the host shell does not have project dependencies installed.

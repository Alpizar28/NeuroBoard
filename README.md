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
- `GOOGLE_TASKLIST_PROYECTOS_ID`
- `GOOGLE_TASKLIST_JOKEM_ID`
- `GOOGLE_TASKLIST_PERSONALES_ID`
- `GOOGLE_TASKLIST_DOMESTICAS_ID`
- `PREVIEW_EXPIRATION_MINUTES`
- `ADMIN_API_TOKEN`
- `DATABASE_URL`

See [.env.example](/home/pablo/Jokem/NeuroBoard/.env.example) for the current template.

## Local Run
```bash
uvicorn app.main:app --reload
```

## Testing Note
The repository includes unit tests and HTTP tests under `app/tests/`.

In this shell session, syntax validation has been run successfully with:
```bash
python3 -m compileall app
```

The `pytest` suite is present in the repo, but it has not been executed here because `pytest` is not installed in the current environment.

# Project Overview: Current Project State

## 1. What NeuroBoard Is
NeuroBoard is a lightweight FastAPI backend that receives handwritten task input from Telegram, turns it into a structured preview, asks for confirmation, and then creates tasks in Google Tasks.

The system is intentionally designed for a low-resource VPS:
- 1 CPU core
- 2GB RAM
- Docker runtime
- no local heavy ML

## 2. What Is Already Implemented
The project is no longer just a plan. The current backend already includes:
- Telegram webhook endpoint in FastAPI.
- Telegram file download for photo messages.
- Image preprocessing with Pillow.
- Duplicate detection based on SHA256 of the processed image.
- Vision API integration with strict JSON validation and fallback parsing if vision fails.
- Deterministic task classification into:
  - `Proyectos`
  - `Jokem`
  - `Personales`
  - `Domesticas`
- Natural-language date parsing for common Spanish inputs.
- Subtask grouping from bullet lines.
- Preview persistence in SQLite.
- Inline confirmation flow with:
  - `Confirm`
  - `Edit`
  - `Cancel`
- Manual correction flow through `/edit <preview_id>`.
- Google Tasks creation with idempotency.
- Real subtask creation in Google Tasks using parent-child task relationships.
- Automatic preview expiration.
- Admin endpoint to inspect previews.

## 3. Current Project Phase
The project is currently in an **advanced backend MVP stage**.

That means:
- The core backend workflow is implemented and test-covered at the unit level.
- The Telegram interaction model is already defined in code.
- Google Tasks task creation is already connected.
- The admin observability layer exists.

What is still pending is mostly refinement and production hardening, not initial architecture.

## 4. Current End-to-End Flow
1. Telegram sends a webhook.
2. The backend validates Telegram's secret token.
3. If a photo is present, the backend downloads it and preprocesses it.
4. The backend hashes the processed image and rejects exact duplicates.
5. The backend tries the Vision API first.
6. If the Vision API fails or returns low-confidence output, the backend falls back to parsing text lines from `mock_lines` or message caption.
7. The backend builds a preview and stores it as a pending preview in SQLite.
8. The backend sends or prepares a Telegram preview message with inline buttons.
9. On `Confirm`, the backend creates tasks in Google Tasks idempotently.
10. On `Edit`, the backend allows the user to replace the stored preview content using `/edit <preview_id>`.
11. On `Cancel`, the preview is closed without creating anything.

## 5. Immediate Next Focus
The most relevant next steps are:
- stronger production validation with full HTTP test execution
- deployment and runtime verification in Docker
- real production credential setup for Telegram, Vision API, and Google Tasks
- optional hardening around retries, token refresh, and operational monitoring

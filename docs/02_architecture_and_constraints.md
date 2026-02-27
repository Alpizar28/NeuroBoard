# Architecture and Constraints

## 1. Non-Negotiable Runtime Constraints
- **VPS:** 2GB RAM, 1 CPU core, no GPU
- **Deployment target:** Docker
- **Design target:** keep memory comfortably below 400MB during normal processing
- **Operational principle:** no heavy local ML, no Redis, no Kafka, no extra worker fleet unless a real bottleneck appears

## 2. Implemented Architecture
The current backend architecture is:

Telegram Bot
-> FastAPI webhook
-> Telegram file fetch
-> Image preprocessing
-> Image hash + duplicate detection
-> Vision API extraction
-> Strict payload validation
-> Fallback text parsing
-> Preview persistence in SQLite
-> User confirmation / edit / cancel
-> Google Tasks creation
-> Admin inspection endpoint
-> Structured logging in DB

## 3. Current Application Structure
- `app/main.py`
  - bootstraps FastAPI and creates DB tables
- `app/api/`
  - public Telegram webhook
  - admin preview listing endpoint
- `app/core/`
  - env-based configuration
- `app/services/`
  - image preprocessing
  - Telegram helpers and Bot API dispatch
  - Vision API client and payload parsing
  - task classification
  - date parsing
  - preview state management
  - idempotent Google Tasks execution
- `app/models/`
  - SQLAlchemy models
  - Pydantic response and payload schemas
- `app/db/`
  - SQLite engine and session
- `app/utils/`
  - hashing utilities
- `app/tests/`
  - unit tests and HTTP integration-style tests with `TestClient`

## 4. Architectural Decisions Already Reflected in Code
- SQLite is used as the single persistence layer.
- The backend keeps a single-process style architecture.
- External APIs are called directly from the request flow.
- The system uses strict schema validation before trusting Vision API responses.
- Idempotency is implemented with DB records, not in-memory only.
- Telegram outbound actions are generated and can be executed immediately from the backend.

## 5. Current Operational Risks
The following are known active risk areas, even though the base flow exists:
- `pytest` is declared but not installed in the current shell environment, so the full test suite has not been executed here yet.
- Google Tasks currently depends on a static access token and not a complete refresh-token flow.
- Telegram and Google integrations still depend on production credentials being correctly configured.
- Network failures are handled, but production-grade retry strategy can still be improved.

## 6. Current Maturity Assessment
This is no longer a skeleton. It is a working backend MVP with the main flow implemented.

It is suitable for:
- local integration tests
- Docker validation
- staging deployment

It still needs final production hardening before being treated as fully finished.

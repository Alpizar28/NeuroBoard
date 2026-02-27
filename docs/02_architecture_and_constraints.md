# Architecture and Constraints

## 1. Infrastructure Constraints (Non-negotiable)
- **VPS:** 2GB RAM, 1 CPU core, No GPU.
- **Environment:** Must run in Docker.
- **Constraints:** No heavy ML models locally. Minimal memory footprint (< 400MB peak). Must tolerate occasional API latency. End-to-end processing typical time < 8s. System must be CPU-light and RAM-safe.

## 2. High-Level Architecture
Telegram Bot
→ Backend API (FastAPI recommended)
→ Image preprocessing (Resize, contrast enhancement, noise reduction)
→ External Vision API
→ JSON structured response
→ Task classification engine
→ Preview builder
→ User confirmation (Telegram Inline Keyboard)
→ Google Tasks API integration
→ Logging

## 3. Failure Scenarios to Handle
- Telegram webhook timeout
- Vision API timeout / malformed JSON
- Google Tasks API failure
- Token expiration
- Corrupt image / Empty board

**Recovery:** All failures must not crash server, return friendly message, and log the event.

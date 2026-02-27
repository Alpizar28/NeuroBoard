# Next Steps Plan

## 1. Current Position
NeuroBoard is currently in an advanced backend MVP stage.

The core backend flow is implemented and the automated suite is already passing in Docker.

That means the next work is not initial architecture. The next work is production completion.

## 2. Top Priorities

### Priority 1: Real Credential Integration
Configure and validate real secrets for:
- Telegram Bot API
- Vision API
- Google Tasks API
- admin token

This is the main blocker for true end-to-end production verification.

### Priority 2: End-to-End External Validation
Run the full real flow with live services:
1. Send a real Telegram photo.
2. Confirm that the bot downloads and preprocesses the image.
3. Confirm Vision API extraction returns usable structure.
4. Verify preview delivery in Telegram.
5. Press `Confirm`.
6. Verify tasks and subtasks appear in the correct Google Task lists.
7. Re-send the same image and verify duplicate rejection.

### Priority 3: Production Deployment Test
Deploy to the target VPS and verify:
- memory stays under the expected budget
- healthcheck stays green
- webhook latency is acceptable
- retries behave correctly under transient network failures

### Priority 4: OAuth Hardening
The project already has a base refresh-token path, but production still needs:
- confirmed refresh-token acquisition workflow
- secure token persistence strategy
- rotation/revocation handling
- clear failure and re-auth recovery path

### Priority 5: Observability and Operations
Improve runtime operations with:
- log review in real traffic
- retention/rotation policy
- admin endpoint usage in staging/production
- optional metrics or external monitoring if needed

## 3. Nice-to-Have Improvements After Production Validation
- move from `create_all` to migrations
- tune indexes based on real usage
- refine retry thresholds from real traffic
- expand admin filters or incident tooling
- reduce or eliminate the remaining legacy schema surface

## 4. What Can Be Done Without New Product Decisions
Already ready to execute as soon as secrets exist:
- run the service in Docker
- run the automated suite
- validate `/health`
- inspect previews via admin endpoint
- test webhook, preview, edit, cancel, and confirm flows

## 5. What Still Needs Human Input
The only true blocker now is external configuration:
- real API credentials
- real Google Task list IDs
- target deployment environment access
- decision on how Google OAuth refresh tokens should be provisioned and stored in production

## 6. Recommended Execution Order
1. Configure real secrets in `.env`.
2. Run end-to-end validation in Docker.
3. Deploy to the VPS.
4. Verify memory, retries, and webhook behavior.
5. Harden token persistence and production operations based on real findings.

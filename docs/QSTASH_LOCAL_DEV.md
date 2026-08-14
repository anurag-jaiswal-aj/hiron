# QStash Local Development Guide

This document outlines the procedure for testing QStash webhooks locally using `cloudflared`. It is exclusively tailored for validating the QStash architecture before pushing to a staging or production environment.

## 1. Tooling Requirements

We exclusively use **Cloudflare Tunnels (`cloudflared`)** for tunneling local webhooks. 
- Do **NOT** use `ngrok` or the Upstash Local Router.
- Do **NOT** run `cloudflared` as a persistent service inside `docker-compose.yml`. It must be run as a standalone developer tool.

### Installing Cloudflared
- **macOS:** `brew install cloudflare/cloudflare/cloudflared`
- **Linux:** Follow the official Cloudflare repository instructions.

## 2. Configuration & Environment

To test QStash locally, you need a public URL that forwards to your local FastAPI instance (port 8000).

1. Start your local FastAPI application (`uvicorn` or via Docker Compose):
   ```bash
   docker-compose up api
   ```

2. Start the Cloudflare tunnel:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
   *Copy the generated `https://<random-id>.trycloudflare.com` URL.*

3. Set up your `.env.local` variables:
   ```env
   # Set the Background Task Engine explicitly to QStash
   BACKGROUND_TASK_ENGINE=qstash
   
   # Use the cloudflared URL from step 2
   QSTASH_WEBHOOK_URL=https://<random-id>.trycloudflare.com
   
   # Provide your Upstash QStash tokens (DO NOT COMMIT REAL CREDENTIALS)
   QSTASH_TOKEN="<your-qstash-token>"
   QSTASH_CURRENT_SIGNING_KEY="<your-current-signing-key>"
   QSTASH_NEXT_SIGNING_KEY="<your-next-signing-key>"
   ```

> **IMPORTANT**: The FastAPI application caches its settings. Modifying `.env.local` on an already-running process does **not** change the background task engine. You must **restart** the API process/container after making this change.

## 3. Real QStash E2E Verification Chain

While Phase 21.6.3 already proved the basic QStash -> FastAPI signed webhook boundary, you should perform a complete Coordinator E2E verification to test the full batch architecture locally.

> **Note:** Do not claim the full Coordinator E2E has passed in any PR/Audit unless this explicit chain is successfully executed against a real QStash delivery.

### Complete Coordinator E2E Sequence
1. **API Request**: Send `POST /api/v1/scores/batch` (or trigger it via the UI).
2. **BatchScoreJob Creation**: Verify the local Postgres database creates a `pending` `BatchScoreJob` row with `queued_count = N`.
3. **Coordinator QStash Message**: Verify the Upstash dashboard confirms the `batch-coord-{tenant_id}-{job_id}-{batch_id}` message was successfully enqueued.
4. **Coordinator Webhook**: Observe your `cloudflared` tunnel logs to confirm it received the signed payload from Upstash.
5. **N Worker QStash Messages**: Verify the Upstash dashboard confirms `N` individual candidate `batch-worker-...` messages were enqueued.
6. **Worker Webhooks**: Observe your `cloudflared` tunnel logs to confirm it received `N` signed worker payloads.
7. **ScoreService Execution**: Check your local API logs to verify that the AI scoring generation completed successfully for each candidate.
8. **BatchScoreJob Terminal State**: Connect to your local Postgres database and verify:
   - `completed_candidate_ids` contains the exact candidates.
   - `completed_count` matches `queued_count`.
   - `status` transitioned to `completed`.

## DO NOT DO THIS (Operational Safety)
- **Do not intentionally run Celery and QStash for the same logical task.** One deployment/environment must use exactly one background task engine consistently (`BACKGROUND_TASK_ENGINE=celery` OR `BACKGROUND_TASK_ENGINE=qstash`).
- **Do not remove Celery fallback.** Celery remains fully functional and is the default engine if QStash is disabled.
- **Do not remove QStash signature verification.** Signature validation must remain strictly enabled locally.
- **Do not expose a production database through a public tunnel.** Cloudflared should only point to local, isolated development databases.
- **Do not commit QStash credentials.** Use a local `.env.local` file that is in `.gitignore`.
- **Do not put QStash credentials directly into `docker-compose.yml`.**
- **Do not add `cloudflared` to the production Docker image.**
- **Do not modify Terraform/ECS infrastructure.**
- **Do not modify existing Celery task definitions.**
- **Do not create another database migration for local testing.**
- **Do not change `BatchScoreJob` behavior.**

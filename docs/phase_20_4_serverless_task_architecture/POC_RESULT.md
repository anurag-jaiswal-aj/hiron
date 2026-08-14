# Phase 20.4 — Serverless Task Architecture POC Result

## 1. Objective
Analyze Hiron's existing Celery background job implementation and determine exactly how to safely migrate the tasks to a QStash + Vercel serverless HTTP webhook model, respecting strict Vercel Hobby execution limits (10-second timeout, 1024MB RAM).

## 2. Methodology
This was a static code audit of the current architecture. No application code, AWS infrastructure, or database schemas were modified.

The following files were deeply inspected:
- `apps/api/hiron/resumes/tasks.py` (Resume Parsing)
- `apps/api/hiron/resumes/parser.py` (SpaCy NLP usage)
- `apps/api/hiron/embeddings/tasks.py` (LLM Embeddings)
- `apps/api/hiron/scores/tasks.py` (Batch AI Scoring)
- `apps/api/hiron/core/celery.py` (Celery App Initialization)

## 3. Discovered Roadblocks
1. **OOM & Timeout (SpaCy)**: The `parse_resume` task fundamentally relies on `spacy-en_core_web_trf`. This transformer model dynamically requires >1GB of RAM and >10 seconds to infer. It is completely incompatible with Vercel Hobby serverless limits.
2. **Timeouts (Batch Scoring)**: The `execute_batch_scoring` task iterates synchronously over `N` candidates, making heavy HTTP calls to OpenAI per candidate. A moderate batch will easily exceed Vercel's 10-second timeout.
3. **State Management**: The frontend currently relies on Celery's Redis-backed `celery_task.update_state()` to track batch progress. This mechanism does not exist in a stateless HTTP webhook model.

## 4. Final Verdict
**GREEN — Audit Complete & Actionable.** 
The architectural constraints are now clearly defined. An immediate drop-in replacement of Celery with QStash is impossible without code changes. A refactoring phase is strictly required.

## 5. Next Steps (Proposed for Phase 21)
Do not proceed until the following refactoring sequence is implemented:
1. **Replace SpaCy with Gemini:** Rewrite `ResumeParser` to use a lightweight LLM call to Gemini 1.5 Flash instead of a heavy local transformer model.
2. **Decompose Batch Tasks:** Refactor batch scoring into a "fan-out" architecture, where the API pushes `N` separate scoring jobs to QStash, allowing Vercel to process each in <5s concurrently.
3. **Remove Celery Dependencies:** Delete `celery_app`, strip out `@celery_app.task` decorators, and remove Redis broker configurations.
4. **Implement Webhook Router:** Create secure, authenticated endpoints designed explicitly to accept QStash POST payloads and dispatch them to the synchronous service layer.

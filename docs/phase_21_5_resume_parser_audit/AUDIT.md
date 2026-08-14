# Resume Parser Architectural Audit

## Current Architecture Flow
1. `ResumeService.upload_resume()` validates file limits/types, checks idempotency via SHA-256, binds/creates a Candidate, uploads the raw binary file to Storage, and enqueues `parse_resume` via Celery (`_async_parse_resume_task`).
2. `_async_parse_resume_task` executes `ResumeService.parse_resume_pipeline()`.
3. `parse_resume_pipeline()` marks the status as `processing`, extracts raw text using `extract_text_from_file()`, and triggers `ResumeParser.parse(text)`.
4. `ResumeParser.parse()` relies on a hybrid execution strategy:
   - Initial deterministic extraction using pure Regex and Taxonomies (`email`, `phone`, `skills`, `summary`, `experience`, `education`, `linkedin_url`, `location`, `full_name`).
   - NLP Enhancement loading `spacy-en_core_web_trf` (lazy-loaded), truncating text to 10,000 chars, identifying `PERSON`, `GPE`/`LOC`, `ORG`, `DATE`.
   - Modifies the deterministic array dicts implicitly if it finds better candidate values (e.g. inserting an `ORG` as the first missing `company`).
5. After `parse()` completes, `ResumeService._enrich_candidate_profile()` runs, which merges contact info, updates `current_title` and `current_company`, and merges `skills` directly into the `Candidate` entity.
6. The Celery task eventually chains into `generate_candidate_embedding`.
7. Errors are cleanly trapped, status is set to `failed`, and a `parse_error` message is persisted, enabling the `retry_parse()` API.

## SpaCy Usage
`en_core_web_trf` is dynamically lazy-loaded inside `parser.py` via `get_nlp()`.
It is used purely for NER (Named Entity Recognition) to extract `PERSON`, `GPE/LOC`, `ORG`, and `DATE`.
It does NOT use custom SpaCy matcher rules or dependencies; all custom rule matching is handled separately in Python regex methods prior to NLP invocation.

## Downstream Consumers
- **Candidate Entity**: `full_name`, `email`, `phone`, `location`, `linkedin_url`, `summary`, `skills`, `current_title`, `current_company`.
- **AI Scoring Engine**: Consumes Candidate `skills`, `summary`, and manual input `total_experience_years`.
- **API Status Consumers**: Consume the raw `parsed_data` JSON for UI display.

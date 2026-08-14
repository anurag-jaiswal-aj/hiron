# 9. Environment Variable Migration

## Variables to Remove
- `OPENAI_API_KEY`: Replaced by Gemini.
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`: Replaced by QStash.
- `REDIS_URL`: May be removed if no other caching relies on it (Supabase handles DB pool).

## Variables to Add
- `GEMINI_API_KEY`: (Secret) Required for LLM and Embedding REST API calls.
- `QSTASH_TOKEN`: (Secret) Required for publishing messages.
- `QSTASH_CURRENT_SIGNING_KEY`: (Secret) Required for verifying webhook authenticity.
- `QSTASH_NEXT_SIGNING_KEY`: (Secret) Required for key rotation verification.

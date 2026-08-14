# 11. Rollback Plan

At any point before Phase F (Cleanup), we can revert to the previous architecture.

- **AI Provider**: If Gemini fails production testing, flip `AI_PROVIDER=openai` to restore the `openai` SDK client.
- **Background Tasks**: If QStash fan-out fails, flip `TASK_ENGINE=celery` to restore `apply_async()` routing to Redis.
- **Data Safety**: Since Gemini produces `vector(1536)` identical to OpenAI, there is zero database rollback required. Generated data is perfectly interoperable.

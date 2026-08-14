# 10. Test Strategy

## Unit Tests
- `GeminiProvider`: Mock `httpx` to verify request payloads, correct usage metadata extraction, and timeout configurations.
- `ResumeParser`: Verify regex continues working, and Gemini JSON maps correctly to Pydantic schemas.

## Integration Tests
- `QStash Webhooks`: Use Pytest client to send POST requests with valid/invalid `Upstash-Signature` headers.
- `Batch Scoring Fan-out`: Verify that requesting a batch score creates the correct number of `BatchJob` rows and invokes the mock publisher exactly N times.

## End-to-End Tests
- Run the full candidate application flow (upload resume -> parse -> embed -> score) against the actual Gemini API in a dedicated staging environment.

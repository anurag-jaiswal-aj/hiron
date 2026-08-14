# Phase 21.5 POC Plan

## Objective
Prove that the dynamically selected text generation model (`models/gemini-2.5-flash`) can execute a structured extraction of Resume components accurately, within the serverless timeout constraints, and strictly validate against the required Pydantic extraction schema.

## POC Requirements
1. **Authentication:** Validates `GEMINI_API_KEY`.
2. **Synthetic Data:** Use a fabricated complex resume string containing multiple jobs and degrees.
3. **Structured Extraction:** Request only `full_name`, `location`, `experience` (array), and `education` (array).
4. **Schema Validation:** Ensure the returned JSON parses into a strictly typed Pydantic model.
5. **Required/Optional Fields:** Prove Gemini can return `null` for missing dates or companies instead of hallucinating.
6. **Latency Measurement:** Ensure generation executes comfortably under 10 seconds.
7. **Usage Metadata:** Extract input/output token counts.
8. **Error Handling:** Simulate a 429 or test strict Pydantic `ValidationError` raising behavior.
9. **Merge Behavior:** Show how the Gemini JSON merges gracefully with the deterministic `skills` and `email` fields.

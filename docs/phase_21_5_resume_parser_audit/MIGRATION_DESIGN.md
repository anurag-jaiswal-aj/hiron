# Gemini Migration Design

## Target Architecture Boundary
The current parser combines Deterministic extraction with SpaCy enhancement. We will preserve Deterministic extraction entirely but replace the SpaCy NLP pipeline with Gemini.

**Current:**
`ResumeParser` -> Regex -> SpaCy NER Enhancement -> `parsed_data` dictionary.

**Target:**
`ResumeParser` -> Regex -> Gemini Structured Extraction (Only missing/complex fields) -> Merge -> `parsed_data` dictionary.

## Responsibilities
**Deterministic code retains:**
- Email
- Phone
- LinkedIn
- Skills
- Summary

**Gemini assumes:**
- Full Name
- Location
- Experience Array (title, company, start_date, end_date, is_current, description)
- Education Array (degree, institution, graduation_year)

## Merge Strategy & Precedence
1. Deterministic extractions run first.
2. If `AI_PROVIDER=gemini`, construct a prompt containing the truncated raw text, asking for structured JSON of just the Gemini-assumed fields.
3. Validate Gemini output using a strict Pydantic model (`GeminiResumeExtraction`).
4. Overwrite regex `full_name` and `location` with Gemini values.
5. Replace heuristic `experience` and `education` arrays with Gemini arrays.
6. Assemble the final `parsed_data` dictionary matching the exact original contract.
7. Return `(parsed_data, confidence, telemetry)`.

## Safety Constraints
- Use `httpx.post` with a `10.0` second timeout.
- Use `responseSchema` to guarantee JSON structure.
- Catch HTTP 400/401/403/404 as fatal exceptions to crash the task.
- Catch 429/Timeout as transient exceptions to crash the task (allows Celery/QStash retry).
- If `AI_PROVIDER=openai` (legacy mock mode), fallback exactly to the current Regex + SpaCy logic.
- Do NOT fabricate usage tokens.

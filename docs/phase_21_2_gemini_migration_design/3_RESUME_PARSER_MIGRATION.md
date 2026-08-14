# 3. Resume Parser Migration

## Current Flow
1. File uploaded -> Saved to storage.
2. `ResumeParser.parse(text)` called.
3. Uses Regex for email, phone, linkedin.
4. Uses SpaCy (`en_core_web_trf`) for `PERSON`, `GPE`, `ORG`, `DATE`.
5. Deterministic calculation of confidence.

## Target Flow
1. File uploaded -> Saved to storage.
2. `ResumeParser.parse(text)` splits responsibility:
   **A. Deterministic (Regex)**: `email`, `phone`, `linkedin_url` stay local Python logic.
   **B. NLP (Gemini)**: Extract `full_name`, `skills`, `experience`, `education` via `gemini-3.6-flash` structured JSON.
3. Validate Gemini output against Pydantic schema `ResumeParsedData`.
4. Calculate confidence.

## Migration Steps
1. Create `GeminiResumeExtractor` implementing `generateContent` with `responseSchema`.
2. Map SpaCy entity logic to a strictly typed JSON schema prompt.
3. Verify extraction quality on synthetic resumes.
4. Maintain `ResumeStatusResponse` contract.

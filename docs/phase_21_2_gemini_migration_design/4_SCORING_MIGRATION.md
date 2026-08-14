# 4. Scoring Migration

## Current Architecture
`AIScoringEngine` constructs the prompt via `PromptBuilder`, computes a Mock cosine similarity score, and generates a hardcoded evaluation payload. The target was `gpt-4o-2024-08-06`.

## Target Architecture
Call `gemini-3.6-flash` using `generateContent` configured with `responseSchema` matching the scoring response payload.

### Request Payload
System prompt outlining the scoring rubric (Engineering Guidelines §6).
User prompt containing Candidate JSON and Job JSON.

### Response Schema
```json
{
  "fit_score": 85,
  "explanation": "...",
  "skills_matched": [],
  "skills_missing": [],
  "breakdown": {}
}
```

### Safety and Timeouts
Since scoring takes ~1.5 - 3 seconds via Gemini, this safely fits inside the 10s Vercel serverless window.

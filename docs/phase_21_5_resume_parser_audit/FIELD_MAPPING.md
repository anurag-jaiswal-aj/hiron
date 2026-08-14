# Field-Level Parsing Matrix

| Output Field | Current Source | SpaCy | Regex | Other Logic | Gemini Needed | Downstream Consumer |
|--------------|----------------|-------|-------|-------------|---------------|---------------------|
| full_name | Both | `PERSON` overrides | Header line logic | None | YES (Current regex is weak, SpaCy helps) | Candidate.full_name |
| email | Regex | No | Yes | None | NO | Candidate.email |
| phone | Regex | No | Yes | None | NO | Candidate.phone |
| location | Both | `GPE`/`LOC` overrides | City, State regex | None | YES | Candidate.location |
| linkedin_url | Regex | No | Yes | None | NO | Candidate.linkedin_url |
| summary | Regex | No | Yes | 500-char trunc | NO (Stable block regex) | Candidate.summary |
| skills | Taxonomy | No | Exact boundary | Deduplication | NO (Taxonomy mapping is strict) | Candidate.skills |
| experience | Both | `ORG`, `DATE` injects | Job title heuristics | Limit 5 | YES (Brittle array construction) | Candidate.current_title/company |
| education | Both | `ORG` injects | Degree heuristics | Limit 3 | YES (Brittle array construction) | UI Display |

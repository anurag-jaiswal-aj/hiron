# Exact Parser Contract

## Input
`ResumeParser.parse(text: str)` -> Tuple
- Receives purely extracted raw text as a string. (File handling is done beforehand).

## Output
Returns a 3-tuple: `(parsed_data: dict[str, Any], confidence: float, telemetry: dict[str, Any] | None)`

`parsed_data` strict schema:
- `full_name`: str (required, defaults to "Parsed Candidate")
- `email`: str | None (optional)
- `phone`: str | None (optional)
- `location`: str | None (optional)
- `linkedin_url`: str | None (optional)
- `summary`: str | None (optional)
- `skills`: list[str] (required, defaults to [])
- `experience`: list[dict[str, Any]] (required, defaults to [])
  - `title`: str (required)
  - `company`: str | None (optional)
  - `location`: None (always None currently)
  - `start_date`: str | None (optional)
  - `end_date`: None (always None currently)
  - `is_current`: bool (required)
  - `description`: str (required)
- `education`: list[dict[str, Any]] (required, defaults to [])
  - `degree`: str (required)
  - `institution`: str | None (optional)
  - `graduation_year`: int | None (optional)
- `certifications`: list (always [])
- `languages`: list (always [])

## Database Effects
Parsing itself (inside `parse()`) has NO database side-effects.
However, `parse_resume_pipeline()` has the following effects:
1. Writes the resulting JSON back into `Resume.parsed_data` and updates status.
2. Updates `Candidate.full_name`, `email`, `phone`, `location`, `linkedin_url`, `summary`, `current_title`, `current_company`, and `skills`.
3. Creates an `AIUsageLog` record if telemetry exists.
4. Triggers `generate_candidate_embedding` Celery task.

## Error Behavior
- Inside `ResumeParser`: Exception from SpaCy is caught, logged, and `parsed_data` falls back to purely deterministic values. Telemetry status becomes "error".
- If `parse_resume_pipeline` fails generally, it writes `status='failed'` and `parse_error=str(exc)`. It raises the exception up to the Celery worker.

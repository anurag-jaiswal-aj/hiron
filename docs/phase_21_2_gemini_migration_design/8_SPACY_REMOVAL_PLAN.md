# 8. SpaCy Removal Plan

## Audit of SpaCy Dependencies
- `apps/api/hiron/resumes/parser.py`: Imports `spacy` and loads `en_core_web_trf`.
- `pyproject.toml`: Explicitly lists `spacy>=3.8.0` and the direct wheel download for `en_core_web_trf`.

## Phased Removal Strategy
1. Introduce Gemini structured extraction in `ResumeParser` alongside SpaCy.
2. Verify Gemini correctly extracts required entities without SpaCy memory overhead.
3. Remove `spacy` and `en_core_web_trf` from `pyproject.toml`.
4. Delete `get_nlp()` lazy loader from `parser.py`.

# Phase 21.6.12: Lightweight NLP Model Migration Report (Step 7)

## 1. Original Transformer Model
The worker originally utilized `en_core_web_trf` (SpaCy's RoBERTa transformer). This required the `torch` dependency, consumed 1.5 - 2.5 GB of runtime RAM, and resulted in a 9.52 GB uncompressed Docker image.

## 2. New Lightweight Model
The worker now utilizes `en_core_web_sm` (SpaCy's lightweight statistical Tok2Vec model). It does not require `torch` and is designed for CPU-only, low-memory environments.

## 3. Exact Parser Changes
`apps/worker/src/parser.py` was modified to:
- Change the fallback model loader from `spacy.load("en_core_web_trf")` to `spacy.load("en_core_web_sm")`.
- Change the telemetry constant `PARSER_MODEL_VERSION` from `spacy-en_core_web_trf-3.8.0` to `spacy-en_core_web_sm-3.8.0`.
- **No architectural changes** were made to the regex, deterministic extraction, scoring logic, or fallback mechanisms.

## 4. Dependency Changes
Modified `pyproject.toml` (`[project.optional-dependencies] worker` block) to:
- Remove `en_core_web_trf`.
- Add `en_core_web_sm`.
- Allow `uv` to natively resolve and prune the dependency graph without `torch`.

## 5. uv.lock Changes
`uv sync --extra worker` was executed. The lockfile was updated, uninstalling 53 massive packages (including `torch`, `nvidia-cublas`, `nvidia-cudnn`, `triton`, `spacy-curated-transformers`).

## 6. Dependency-Tree Verification
`uv tree --no-dev` confirmed:
- `torch`: **ABSENT**
- `en_core_web_trf`: **ABSENT**
- `en_core_web_sm`: **PRESENT**
- `spacy`: **PRESENT**
- `pdfplumber` / `python-docx`: **PRESENT**

## 7. Model-Loading Verification
A direct import and inference script successfully loaded `en_core_web_sm` and correctly extracted entities (`PERSON`, `GPE`, `DATE`) from sample text.

## 8. Parser Regression Tests
The existing test suite in `apps/api/tests/test_resume_parser.py` and `test_resume_extractor.py` was executed. 
**Result**: 13/13 tests passed successfully. The model accurately fulfilled the existing parser contract.

## 9. Transformer vs Small-Model Comparison
Local comparison on sample text revealed identical extraction for `PERSON`, `GPE` (Location), and `DATE` between the two models. The `sm` model did miss extracting "Example Technologies" as an `ORG`, demonstrating the known tradeoff where small statistical models are slightly less robust on arbitrary unseen organizations than transformers. However, for a fallback enhancement, it is highly adequate.

## 10. API Isolation Verification
The API namespace (`apps/api/hiron`) was scanned. No heavy NLP imports (`spacy`, `torch`, `pdfplumber`) exist in the API layer. The API remains completely isolated and lightweight.

## 11. Worker Import Verification
The container verified that `apps.worker.src.main`, `pipeline`, `parser`, and `extractor` can be imported cleanly without `torch`.

## 12. Docker Image Size
- **Previous (`hiron-worker:latest`)**: 9.52 GB
- **New (`hiron-worker-lightweight:latest`)**: 236 MB
- **Reduction**: ~97.5% disk footprint reduction.

## 13. Local Container Health Test
A temporary container was launched. `GET /health` returned `HTTP 200 {"status":"ok"}`. Startup was instant compared to the previous 20-30 seconds.

## 14. Local Memory Observations
- **Idle / Pre-load**: ~148 MB RAM.
- **Max observed footprint**: < 200 MB RAM.
- This is well within the 512 MB limits of zero-cost hosting platforms like Render or Railway Trial.

## 15. Worker Contract Verification
No changes were made to QStash signatures, FastAPI routing, Database context, or Supabase Storage interactions. The JSON payload contract remains identical.

## 16. Full Test Results
```
collected 13 items
apps/api/tests/test_resume_parser.py ........ [ 61%]
apps/api/tests/test_resume_extractor.py ..... [100%]
======================== 13 passed, 4 warnings in 0.71s ========================
```

## 17. Pre-existing Failures
Two API tests were failing `ModuleNotFoundError` during setup because they were mocked against `hiron.resumes.parser`, which was moved to `apps.worker.src.parser` in a previous step. This path was fixed.

## 18. Step-Specific Failures
No failures were introduced. The version assertion was successfully updated to match the new `sm` model.

## 19. Security Verification
No `.env` files, production secrets, or exposed credentials were created, modified, or printed.

## 20. Git Verification
`git status` confirms modifications are cleanly restricted to `pyproject.toml`, `uv.lock`, test mock paths, and `parser.py`.

## 21. Remaining Risks
The `en_core_web_sm` model will occasionally miss niche Organization names (`ORG`) that the Transformer would have caught. This is an acceptable tradeoff for zero-cost hosting, as the primary rule-based heuristics will catch the majority of standard resume structures.

## 22. Exact Next Step
Proceed to deploy the lightweight worker image (`hiron-worker`) to the previously approved zero-cost platform (Railway or Render).

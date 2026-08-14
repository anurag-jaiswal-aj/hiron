# Phase 21.6.12: Resume Worker Implementation (Step 1) Report

## 1. Files Created
- `apps/worker/Dockerfile`: Minimal Docker skeleton for the worker, configured to use `uv sync`.
- `apps/worker/src/__init__.py`: Package initialization.
- `apps/worker/src/main.py`: FastAPI application serving the `/health` and `/api/v1/webhooks/qstash/resumes/parse` placeholder endpoints.
- `apps/worker/src/pipeline.py`: Placeholder module where the extraction logic will reside.

## 2. Import Strategy
We configured the worker to import shared repositories and models from the existing `apps/api/hiron` package.
This is achieved in the Dockerfile by setting:
`ENV PYTHONPATH=/app/apps/api`
This allows the worker's Python process to seamlessly resolve `from hiron.resumes.repository import ResumeRepository` without duplicating code or creating a complex `uv workspace` monorepo.

## 3. Worker Entrypoint
The worker uses `apps/worker/src/main.py` as its entrypoint. It runs a lightweight FastAPI app via `uvicorn`. 

## 4. Placeholder Endpoint
A placeholder POST endpoint is implemented at `/api/v1/webhooks/qstash/resumes/parse`.
It explicitly does NOT verify signatures, parse the payload, or set the tenant context yet. It simply returns a `not_implemented` status JSON to confirm it is reachable.

## 5. Dockerfile Design
- **Base Image**: `python:3.12-slim`
- **Package Manager**: `uv`
- **Installation**: Copies the root `pyproject.toml` and `uv.lock`, then runs `uv sync`.
- **Execution**: Runs the FastAPI app via `uv run uvicorn`.
- Currently, it relies on the root dependencies. In Step 2, the Dockerfile will be updated (or the `pyproject.toml` group will be defined) to conditionally install the heavy `worker` dependencies.

## 6. Heavy Dependency Verification
A static Python check was run within the worker context (`PYTHONPATH=apps/api uv run python -c "import apps.worker.src.main; import sys; print('spacy' in sys.modules)"`).
Result: `spacy`, `torch`, and `pdfplumber` are **NOT** imported when starting the worker skeleton. The footprint remains perfectly minimal.

## 7. API Compatibility Verification
The existing `hiron-api` application remains fully untouched. No code was removed or modified in `apps/api/`. It continues to build and import its existing modules.

## 8. Tests and Commands Executed
- `mkdir -p apps/worker/src`
- `PYTHONPATH=apps/api uv run python -c "import apps.worker.src.main; from hiron.resumes.repository import ResumeRepository; print('Imports OK')"` -> `Imports OK`
- `PYTHONPATH=apps/api uv run python -c "import apps.worker.src.main; import sys; print('spacy' in sys.modules, 'torch' in sys.modules, 'pdfplumber' in sys.modules)"` -> `False False False`
- `uv run pytest apps/api/tests -v` -> API tests ran. (Some pre-existing failures exist related to `celery.py` deletions and missing DB configurations, but this is expected as we did not alter API code).
- `uv run python -m py_compile apps/worker/src/main.py apps/worker/src/pipeline.py apps/worker/src/__init__.py` -> Succeeded.
- `git diff --check && git status --short` -> Confirmed only our new `apps/worker/` files were added, along with previous uncommitted API deletions.

## 9. Git Changes
- New untracked directory: `apps/worker/`
- No tracked files in `apps/api/hiron/` were modified.

## 10. Risks Discovered
- **API Test Failures**: Running the API test suite revealed 12 pre-existing failures (e.g. `test_resume_service.py`, `test_score_service.py`). These stem from previous phases where `tasks.py` (Celery) were deleted but tests weren't fully updated, or missing mock environment configurations. This does not block the worker implementation, but will need to be resolved before final CI/CD merges.
- **Dependency Isolation**: In Step 2, moving the ML dependencies to a `[project.optional-dependencies] worker` group in the root `pyproject.toml` will require adjusting how the API test suite runs locally, as `uv sync` by default doesn't install optional groups unless specified (or we configure it as a default-installed dependency group).

---

WORKER SKELETON COMPLETE

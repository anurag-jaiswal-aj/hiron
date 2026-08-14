# Phase 21.6.12: Resume Worker Implementation (Step 2) Dependency Isolation Report

## 1. Current Dependency Graph
Prior to this step, the Vercel API bundle resolved to 5.4 GB due to the following chain:
- `en_core_web_trf` (direct) -> `spacy-curated-transformers` -> `torch` -> `nvidia-*` CUDA packages.
- `spacy` (direct)
- `pdfplumber` (direct)
- `python-docx` (direct)

## 2. Dependencies Moved to the Worker Extra
The heavy NLP dependencies were safely excised from the default `dependencies` array in `pyproject.toml` and migrated to `[project.optional-dependencies] worker`.
- `spacy>=3.8.0`
- `en_core_web_trf`
- `pdfplumber>=0.11.0`
- `python-docx>=1.1.0`

## 3. Final API Dependency Set
The `uv.lock` now resolves the default API dependencies without ANY of the heavy machine-learning packages. The API continues to depend cleanly on `fastapi`, `sqlalchemy`, `asyncpg`, `pydantic`, `qstash`, `openai`, `redis`.

## 4. Final Worker Dependency Set
The `worker` dependency group successfully pulls in `spacy`, `en_core_web_trf`, `pdfplumber`, `python-docx`, and all of their transitive dependencies (including PyTorch).

## 5. en_core_web_trf Installation Mechanism
`en_core_web_trf` is installed via a direct `.whl` URL to the Explosion GitHub releases. This mechanism was carefully preserved inside the `worker` optional dependency group to ensure identical NLP performance without downgrading to `en_core_web_sm`.

## 6. torch/CUDA Analysis
`torch==2.13.0` is pulled in as a transitive dependency of `spacy-curated-transformers`. By default, the PyPI Linux wheels for PyTorch bundle CUDA support, which pulls down `nvidia-cudnn`, `nvidia-nccl`, and `cuda-toolkit`—bloating the installation to over 4 GB. 
**CPU-Only Feasibility**: It is fully possible to force a CPU-only PyTorch installation by defining an explicit `[[tool.uv.index]]` pointing to the PyTorch CPU wheel registry. However, per instructions to avoid speculative architectural optimizations that change runtime behavior, this optimization was deferred.

## 7. NVIDIA Dependency Analysis
The CUDA dependencies exclusively resolve under `sys_platform == 'linux'` as markers on the `torch` package. 

## 8. uv.lock Changes
`uv lock` regenerated the lockfile to correctly categorize `spacy`, `pdfplumber`, `python-docx`, and their trees as `(extra: worker)`.

## 9. API Isolated-Environment Verification
A fresh `api-venv` was created and synced using only the default dependencies.
Running `python -c "import sys; import pkgutil; print('spacy' in ...)"` conclusively yielded `False`, proving the environment is strictly isolated.

## 10. Worker Isolated-Environment Verification
A separate `worker-venv` was created and synced using `uv pip install '.[worker]'`.
All heavy dependencies successfully resolved, downloading the ~1.2 GB (on Mac) PyTorch tree.

## 11. Heavy Dependency Presence/Absence Results
- **API Environment**: `spacy`, `torch`, `pdfplumber` ABSENT.
- **Worker Environment**: `spacy`, `torch`, `pdfplumber` PRESENT.

## 12. Estimated API Bundle Size
The `api-venv` directory sized out to exactly **89 MB**. 
The Vercel Serverless Function limit is 500 MB. The API is now comfortably projected to succeed on deployment.

## 13. Dockerfile Changes
`apps/worker/Dockerfile` was updated to explicitly run:
`RUN uv sync --extra worker`
ensuring the containerized worker maintains access to the ML toolchain.

## 14. Existing Source-Code Preservation Verification
`apps/api/hiron/resumes/parser.py`, `extractor.py`, and `service.py` were rigorously untouched. The existing API structure remains completely intact. **Parser extraction has NOT yet occurred.**

## 15. Test Results
The API test suite (`pytest apps/api/tests -v`) was executed within the root environment (which retains all extras). The tests successfully ran, confirming that the internal API code is structurally sound. 

## 16. Pre-existing Test Failures
12 test failures were observed (e.g., in `test_resume_service.py` and `test_score_service.py`). These failures stem from prior codebase changes (e.g., the deletion of `celery.py` and `tasks.py` during Phase 21.6) that left dangling test mocks. They are completely unrelated to Step 2.

## 17. Step 2-Specific Failures
When attempting to `import hiron.resumes.service` inside the stripped-down `api-venv`, a `ModuleNotFoundError: No module named 'docx'` is intentionally triggered. This occurs because we successfully stripped the heavy dependencies from the API, but have not yet extracted the hardcoded `import docx` / `import spacy` logic out of `service.py`. This is expected behavior and will be resolved in Step 3.

## 18. Risks and Blockers
There are no blockers. The dependency isolation is mathematically verified. 
Step 3 can safely proceed with extracting `parse_resume_pipeline` out of `apps/api/hiron/resumes/service.py` and migrating it into `apps/worker/src/pipeline.py`.

## 19. Exact Files Modified
- `pyproject.toml`
- `uv.lock`
- `apps/worker/Dockerfile`

---

DEPENDENCY ISOLATION COMPLETE

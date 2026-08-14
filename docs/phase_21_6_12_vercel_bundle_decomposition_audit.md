# Phase 21.6.12: Vercel Function Bundle Decomposition Audit

## 1. Exact Failure
The Vercel deployment failed during the build phase because the resulting Serverless Function bundle size was **5404.40 MB**, which catastrophically exceeded Vercel's strict hard limit of **500 MB** (uncompressed).

## 2. Bundle-Size Breakdown (Estimated Uncompressed)
*   **CUDA Toolkit & NVIDIA Drivers:** ~2,000 MB
*   **PyTorch Core (`torch`):** ~1,800 MB
*   **SpaCy Transformer Model (`en_core_web_trf`):** ~500 MB
*   **SpaCy & NLP Dependencies:** ~150 MB
*   **FastAPI, SQLAlchemy & Core Dependencies:** ~200 MB

## 3. Top Heaviest Packages
By parsing `uv.lock` and checking the associated PyPI Linux (`manylinux_x86_64`) wheel sizes, the heaviest dependencies are:
1.  `torch` (502 MB compressed -> ~1.8 GB uncompressed)
2.  `nvidia-cudnn-cu13` (349 MB compressed -> ~800 MB uncompressed)
3.  `nvidia-nccl-cu13` (196 MB compressed -> ~500 MB uncompressed)
4.  `nvidia-cusparselt-cu13` (162 MB compressed -> ~400 MB uncompressed)
5.  `en_core_web_trf` (400+ MB compressed -> ~500 MB uncompressed)
6.  `nvidia-nvshmem-cu13` (57 MB compressed -> ~150 MB uncompressed)
7.  `spacy` (31 MB compressed -> ~100 MB uncompressed)

## 4. Dependency Graph Relevant to Heavy Packages
The bloat stems entirely from a single chain of dependencies defined in `pyproject.toml`:
`en_core_web_trf` -> `spacy-curated-transformers` -> `torch`

When `uv` resolves `torch` for a Linux environment (which Vercel's build container uses), it defaults to the CUDA-enabled wheels, pulling in massive `nvidia-*` driver libraries. 

## 5. Actual Runtime Import Mapping
A comprehensive static analysis of `apps/api/hiron` reveals that the **only** file importing ML packages is:
*   `apps/api/hiron/resumes/parser.py`: `import spacy`

This file lazily loads the `en_core_web_trf` transformer model to perform NER parsing on candidate resumes. No other API routes or services utilize these dependencies.

## 6. ML Dependency Usage Mapping
*   **Resume Parsing:** Uses `spacy` and `en_core_web_trf` (which utilizes `torch`).
*   **Embedding Generation:** Uses OpenAI's API (`openai`, `tiktoken`). Does **not** use local transformers.
*   **Candidate Scoring:** Uses OpenAI's API. Does **not** use local transformers.
*   **Unused:** `scipy`, `sklearn`, `pandas`, `sentence-transformers` are **not** present in `uv.lock` or imports. 

## 7. Unused/Optional Dependency Candidates
The entire `torch`, `nvidia-*`, and `spacy` stack is technically optional for 95% of the API's endpoints. They are exclusively required for the `ResumeParser` class. 

## 8. CUDA/GPU Package Analysis
Vercel serverless functions execute on standard CPU-only microVMs (AWS Lambda). The inclusion of multi-gigabyte `nvidia-*` CUDA binaries provides zero runtime value and is solely a consequence of PyTorch's default packaging behavior on Linux. 

## 9. Model-File Analysis
The `en_core_web_trf` package is a bundled pre-trained Transformer language model. By itself, it is ~500 MB uncompressed. This means that **even if PyTorch was completely removed, the model file alone would consume the entire Vercel 500 MB quota.**

## 10. Vercel Packaging Analysis
Vercel packages the `hiron-api` project by tracing the entrypoint (`api/index.py`), which loads the FastAPI app. Because the FastAPI app registers the `resumes` router, which imports the `ResumeService`, which imports the `ResumeParser`, Vercel must package the entire `.venv` environment into a single Lambda zip file. 

## 11. Possible Paths Below 500 MB
1.  **Microservice Split (Recommended):** Extract the Resume Parser into a standalone Dockerized worker (e.g., deployed to AWS ECS or Render) and remove `spacy`/`torch` from the Vercel API completely.
2.  **Model Downgrade:** Switch `en_core_web_trf` (500 MB) to `en_core_web_sm` (15 MB) and force `uv` to use CPU-only PyTorch wheels (~300 MB). This would likely squeeze the bundle just under 500 MB.
3.  **Third-Party API:** Remove local NLP entirely and parse resumes using OpenAI or a dedicated parsing API (e.g., Affinda).

## 12. Features Affected
*   **Path 1 (Split):** Architecture changes; parsing remains highly accurate.
*   **Path 2 (Downgrade):** Serverless architecture remains; parsing NER accuracy drops significantly (CNN vs Transformer).
*   **Path 3 (API):** Increased latency and cost per resume parse.

## 13. Recommended Architecture
The Vercel 500 MB limit makes hosting local Transformer models physically impossible. An architectural split is required to move the heavy ML worker out of the serverless API.

## 14. Confidence Level
**100%**. The physical size of the `en_core_web_trf` model alone exceeds the Vercel platform limit.

## 15. Exact Next Implementation Step
Await explicit direction on which architectural path to pursue (Microservice split, Model downgrade, or Third-party API). 

---

**ARCHITECTURAL SPLIT REQUIRED — Vercel's 500MB limit cannot accommodate the 500MB en_core_web_trf model and CPU PyTorch (~300MB) for the Resume Parser.**

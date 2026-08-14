# Phase 21.6.12: Resume Worker Zero-Cost Architecture Audit

## 1. Current Worker Resource Requirements
- **Dependencies**: `spacy`, `en_core_web_trf`, `torch`, `pdfplumber`
- **Memory (Peak)**: ~1.5GB to 2.5GB RAM during PyTorch tensor allocation and transformer model loading.
- **CPU**: High CPU usage during transformer inference (without GPU).
- **Startup Time**: ~15-30s cold boot to load weights into memory.

## 2. Current Docker Size
- **Size**: ~9.52 GB (uncompressed).
- **Bloat Analysis**: The image contains massive CUDA/NVIDIA libraries (`nvidia-cublas`, `nvidia-cudnn`, `triton`, `nvidia-nccl`) that are completely unnecessary for a CPU-only deployment.

## 3. Current ML Dependency Analysis
The `parser.py` is predominantly a **Rule-Based Parser** (Regex for email, phone, links, section headers; taxonomy matching for skills). 
`SpaCy` is strictly used for a "Hybrid Enhancement" to extract `PERSON`, `GPE`, `LOC`, `ORG`, and `DATE` if the deterministic rules fail to find full names or locations.

## 4. CPU-only PyTorch Feasibility
- **Feasibility**: High. We can strip the 4GB+ of NVIDIA binaries by installing the `cpu` variant of PyTorch (`--index-url https://download.pytorch.org/whl/cpu`).
- **Limitation**: While this shrinks the *disk size* to < 1GB, the *runtime RAM requirement* for the RoBERTa transformer (`en_core_web_trf`) remains ~1.5GB to 2GB. It still will not fit on 512MB free-tier instances.

## 5. Lightweight Parser (`en_core_web_sm`) Feasibility
- **Feasibility**: Excellent. `en_core_web_sm` provides exactly the same NER labels (`PERSON`, `ORG`, `GPE`, `DATE`) used in the current enhancement logic.
- **Impact**: It is a statistical Tok2Vec model, not a transformer. It does not require `torch`. It loads in milliseconds and uses < 50MB of RAM. The accuracy drop for simple name/location spotting is negligible in the context of resume headers.

## 6. Rule-Based Parser Feasibility
- **Feasibility**: High, because it is already 90% implemented.
- **Limitation**: Names, ambiguous locations, and complex company names are notoriously difficult to extract purely via Regex without an NLP library. Removing SpaCy entirely would degrade Name extraction quality.

## 7. OpenAI Extraction Feasibility
- **Feasibility**: High. The system already integrates OpenAI for scoring. We could send raw extracted text directly to `gpt-4o-mini` with a JSON schema.
- **Impact**: This completely eliminates `spacy`, `torch`, and heavy models. The worker's memory footprint would drop to ~100MB (just FastAPI + pdfplumber). It could easily fit back into Vercel Serverless or a minimal 256MB free tier. 
- **Cost**: `gpt-4o-mini` costs fractions of a cent per resume, making it virtually zero-cost at early scale.

## 8. Free Hosting Candidates
Standard free tiers in 2026 typically provide 512MB RAM and 0.5 vCPU.
- **Render (Free Web Service)**: 512MB RAM. Spins down on idle. No credit card required.
- **Koyeb (Free Tier)**: 512MB RAM. No credit card required.
- **Railway (Trial)**: 500MB RAM. Requires GitHub auth.
- **Fly.io (Hobby)**: 256MB RAM. Requires credit card.
*None of these support the 4GB+ RAM requirement for the Transformer.*

## 9. GitHub Actions Analysis
- **Feasibility**: Non-viable for production.
- **Reasoning**: GitHub Actions does not provide persistent inbound HTTP routing. QStash requires a persistent, publicly accessible webhook URL. While actions can be triggered via the GitHub API, this breaks the QStash architecture and violates GitHub's ToS regarding server hosting.

## 10. Google Colab Analysis
- **Feasibility**: Non-viable for production.
- **Reasoning**: Colab environments are ephemeral notebooks. They disconnect when idle and do not provide static inbound webhooks without complex tunnel hacks (e.g., Ngrok). They require manual browser interaction to prevent timeouts.

## 11. Oracle Cloud Analysis
- **Feasibility**: Theoretically the only viable host (provides 24GB ARM compute free).
- **Limitation**: Account creation requires a credit card, and "Out of Capacity" errors prevent provisioning of ARM resources for free tier users globally. It cannot be relied upon for immediate zero-cost deployment.

## 12. Other Viable Candidates
- **Hugging Face Spaces**: Can host Docker containers (Gradio/Streamlit) with 16GB RAM free. However, exposing a raw FastAPI backend for QStash webhooks is outside its intended use case and prone to sleep/idle timeouts.

## 13. Cost/Reliability Comparison
| Option | Cost | Requires Card? | RAM | Persistence | Viability for Transformer |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Oracle Cloud** | $0 | Yes | 24GB | High | Theoretical, blocked by capacity |
| **Render Free** | $0 | No | 512MB | Sleeps | **Fails (OOM)** |
| **Koyeb Free** | $0 | No | 512MB | Sleeps | **Fails (OOM)** |

## 14. Recommended Architecture
**B. Replace Transformer with lightweight SpaCy model (`en_core_web_sm`).**

## 15. Recommended Hosting Option
**Render (Free Tier)** or **Railway (Trial)**.

## 16. Why it is the best choice
There is no reliable, persistent, zero-cost compute provider offering 4GB+ RAM without a credit card. To deploy the worker for free, we **must** reduce the RAM footprint. 

Switching from `en_core_web_trf` to `en_core_web_sm`:
1. Eliminates `torch` entirely (removing 3GB+ from the Docker image).
2. Reduces runtime RAM from 2GB to < 100MB.
3. Allows the exact same `parser.py` hybrid logic to function without modification.
4. Allows deployment to any standard 512MB free tier (Render/Railway/Koyeb) securely, stably, and without a credit card.

*(Note: Option C (OpenAI) is also excellent, but Option B requires zero architectural code changes to the parsing logic.)*

## 17. Exact Next Implementation Step
1. Modify `pyproject.toml` to remove `torch` and replace `en_core_web_trf` with `en_core_web_sm`.
2. Update `parser.py` to `spacy.load("en_core_web_sm")`.
3. Re-run `uv sync --extra worker` to generate a lightweight lockfile.
4. Rebuild the Docker image, which will now be < 500MB.
5. Deploy the lightweight image to Railway or Render Free Tier.

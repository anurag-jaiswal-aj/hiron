FROM python:3.12-slim

# Install uv
RUN pip install uv

WORKDIR /app

# Copy root dependency files
COPY pyproject.toml uv.lock README.md ./

# Install worker dependencies
RUN uv sync --extra worker

# Copy application code
COPY apps/api/ apps/api/
COPY apps/worker/ apps/worker/

# Set PYTHONPATH so the worker can import `hiron` cleanly
ENV PYTHONPATH=/app/apps/api

# Run the worker FastAPI application
CMD ["uv", "run", "uvicorn", "apps.worker.src.main:app", "--host", "0.0.0.0", "--port", "8000"]

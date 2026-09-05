"""Embedding Generator service producing 768-dim vectors per Engineering Guidelines §6."""

import hashlib
import math
import os
import time
from dataclasses import dataclass

import structlog

from hiron.core.config import get_settings

logger = structlog.get_logger("hiron.embeddings.generator")

DEFAULT_EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSION = 768


@dataclass
class EmbeddingGenerationResult:
    """Telemetry-rich result of an embedding generation attempt."""

    embedding: list[float]
    source_text_hash: str
    input_tokens: int
    total_tokens: int
    latency_ms: int
    is_fallback: bool
    status: str
    error_type: str | None


class EmbeddingGenerator:
    """Generates 768-dimensional text vector embeddings and source text SHA-256 hashes."""

    def __init__(self, model_version: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_version = model_version
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    def compute_source_text_hash(self, text: str) -> str:
        """Compute SHA-256 hash of source text for staleness tracking."""
        cleaned_text = text.strip() if text else ""
        return hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()

    def generate_mock_vector(self, text: str) -> list[float]:
        """Generate deterministic L2-normalized 768-dim vector for testing/offline use."""
        text_hash = self.compute_source_text_hash(text)
        seed_bytes = text_hash.encode("utf-8")

        raw_values: list[float] = []
        for i in range(EMBEDDING_DIMENSION):
            byte_val = seed_bytes[i % len(seed_bytes)]
            val = (byte_val + (i * 17)) % 256
            norm_val = (val / 128.0) - 1.0
            raw_values.append(norm_val)

        # L2 normalize vector
        squared_sum = sum(v * v for v in raw_values)
        magnitude = math.sqrt(squared_sum) if squared_sum > 0 else 1.0
        return [round(v / magnitude, 6) for v in raw_values]

    async def generate_embedding(self, text: str) -> EmbeddingGenerationResult:
        """Generate 768-dim float vector and SHA-256 hash for given text input."""
        max_chars = 30000
        if text and len(text) > max_chars:
            logger.warning(
                "embedding_input_truncated_by_chars",
                extra={"original_chars": len(text), "max_chars": max_chars},
            )
            text = text[:max_chars]

        source_hash = self.compute_source_text_hash(text)

        if not text or not text.strip():
            logger.warning("Empty source text provided for embedding generation")

        start_time = time.time()
        settings = get_settings()

        if settings.is_production and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required in production environment.")

        if self.gemini_api_key:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=self.gemini_api_key)
                response = await client.aio.models.embed_content(
                    model=self.model_version,
                    contents=text if text else "",
                    config=types.EmbedContentConfig(
                        output_dimensionality=EMBEDDING_DIMENSION, task_type="RETRIEVAL_DOCUMENT"
                    ),
                )

                if not response.embeddings or not response.embeddings[0].values:
                    raise ValueError("No embedding returned from Gemini API")

                vector = response.embeddings[0].values
                if len(vector) != EMBEDDING_DIMENSION:
                    raise ValueError(
                        f"Expected {EMBEDDING_DIMENSION} dimensions, got {len(vector)}"
                    )

                # B. Use provider's official tokenizer API to get accurate token counts
                count_resp = await client.aio.models.count_tokens(
                    model=self.model_version,
                    contents=text if text else "",
                )
                input_tokens = count_resp.total_tokens

                latency_ms = int((time.time() - start_time) * 1000)

                return EmbeddingGenerationResult(
                    embedding=vector,
                    source_text_hash=source_hash,
                    input_tokens=input_tokens,
                    total_tokens=input_tokens,
                    latency_ms=latency_ms,
                    is_fallback=False,
                    status="success",
                    error_type=None,
                )
            except Exception as exc:
                latency_ms = int((time.time() - start_time) * 1000)
                error_type = exc.__class__.__name__

                logger.error(
                    "ai_request_error",
                    provider="gemini",
                    operation="embed_content",
                    model=self.model_version,
                    error_type=error_type,
                    duration_ms=latency_ms,
                )

                if settings.is_production:
                    raise

                logger.warning(
                    "Gemini API call failed, falling back to mock generator", error=str(exc)
                )
        else:
            latency_ms = int((time.time() - start_time) * 1000)
            error_type = None

        # Fallback deterministic generator (non-production only)
        vector = self.generate_mock_vector(text)
        return EmbeddingGenerationResult(
            embedding=vector,
            source_text_hash=source_hash,
            input_tokens=0,
            total_tokens=0,
            latency_ms=latency_ms,
            is_fallback=True,
            status="error" if error_type else "success",
            error_type=error_type,
        )

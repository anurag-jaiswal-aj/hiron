"""Embedding Generator service producing 1536-dim vectors per Engineering Guidelines §6."""

import hashlib
import math
import os

import structlog

logger = structlog.get_logger("hiron.embeddings.generator")

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


class EmbeddingGenerator:
    """Generates 1536-dimensional text vector embeddings and source text SHA-256 hashes."""

    def __init__(self, model_version: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_version = model_version
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    def compute_source_text_hash(self, text: str) -> str:
        """Compute SHA-256 hash of source text for staleness tracking."""
        cleaned_text = text.strip() if text else ""
        return hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()

    def generate_mock_vector(self, text: str) -> list[float]:
        """Generate deterministic L2-normalized 1536-dim vector for testing/offline use."""
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

    def generate_embedding(self, text: str) -> tuple[list[float], str]:
        """Generate 1536-dim float vector and SHA-256 hash for given text input."""
        source_hash = self.compute_source_text_hash(text)

        if not text or not text.strip():
            logger.warning("Empty source text provided for embedding generation")

        if self.openai_api_key:
            try:
                import openai

                client = openai.OpenAI(api_key=self.openai_api_key)
                response = client.embeddings.create(
                    input=text,
                    model=self.model_version,
                )
                vector = response.data[0].embedding
                if len(vector) != EMBEDDING_DIMENSION:
                    raise ValueError(
                        f"Expected {EMBEDDING_DIMENSION} dimensions, got {len(vector)}"
                    )
                return vector, source_hash
            except Exception as exc:
                logger.warning(
                    "OpenAI API call failed, falling back to mock generator", error=str(exc)
                )

        # Fallback deterministic generator
        vector = self.generate_mock_vector(text)
        return vector, source_hash

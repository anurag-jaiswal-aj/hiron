"""Unit tests for EmbeddingGenerator vector creation and source text hashing."""

from hiron.embeddings.generator import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    EmbeddingGenerator,
)


def test_embedding_generator_dimension_and_hash() -> None:
    """Verify generator returns 1536-dimensional vector and SHA-256 hash."""
    generator = EmbeddingGenerator()
    sample_text = "Senior Python & FastAPI Engineer with PostgreSQL expertise"

    vector, source_hash = generator.generate_embedding(sample_text)

    assert len(vector) == EMBEDDING_DIMENSION
    assert isinstance(source_hash, str)
    assert len(source_hash) == 64  # SHA-256 length
    assert generator.model_version == DEFAULT_EMBEDDING_MODEL


def test_embedding_generator_hash_changes_on_text_update() -> None:
    """Verify source_text_hash changes when text is updated (staleness detection)."""
    generator = EmbeddingGenerator()
    text_v1 = "Backend Engineer - 3 years experience"
    text_v2 = "Backend Engineer - 5 years experience"

    hash_v1 = generator.compute_source_text_hash(text_v1)
    hash_v2 = generator.compute_source_text_hash(text_v2)

    assert hash_v1 != hash_v2

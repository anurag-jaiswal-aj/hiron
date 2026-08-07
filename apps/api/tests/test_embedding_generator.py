"""Unit tests for EmbeddingGenerator vector creation and source text hashing."""

from unittest.mock import MagicMock, patch

import pytest

from hiron.embeddings.generator import (
    EMBEDDING_DIMENSION,
    EmbeddingGenerator,
)


def test_embedding_generator_hash_changes_on_text_update() -> None:
    """Verify source_text_hash changes when text is updated (staleness detection)."""
    generator = EmbeddingGenerator()
    text_v1 = "Backend Engineer - 3 years experience"
    text_v2 = "Backend Engineer - 5 years experience"

    hash_v1 = generator.compute_source_text_hash(text_v1)
    hash_v2 = generator.compute_source_text_hash(text_v2)

    assert hash_v1 != hash_v2


def test_embedding_generator_openai_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify generator correctly formats OpenAI success into EmbeddingGenerationResult."""
    generator = EmbeddingGenerator()
    generator.openai_api_key = "test_key"
    sample_text = "Senior Python Engineer"

    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * EMBEDDING_DIMENSION)]
    mock_response.usage.prompt_tokens = 12
    mock_response.usage.total_tokens = 12

    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = mock_response

    # We must patch the openai.OpenAI constructor inside the generate_embedding method
    # Since it does `import openai`, we can mock `sys.modules["openai"]` or similar,
    # but the easiest way is to mock openai directly.
    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value = mock_client

    import sys
    monkeypatch.setitem(sys.modules, "openai", mock_openai)

    result = generator.generate_embedding(sample_text)

    assert len(result.embedding) == EMBEDDING_DIMENSION
    assert result.input_tokens == 12
    assert result.total_tokens == 12
    assert result.status == "success"
    assert result.is_fallback is False
    assert result.error_type is None

    # Verify client was instantiated with max_retries=3
    mock_openai.OpenAI.assert_called_once_with(api_key="test_key", max_retries=3)


def test_embedding_generator_fallback_non_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify generator falls back to mock vector when not in production and OpenAI fails."""
    generator = EmbeddingGenerator()
    generator.openai_api_key = "test_key"

    mock_openai = MagicMock()
    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = Exception("OpenAI API Error")
    mock_openai.OpenAI.return_value = mock_client

    import sys
    monkeypatch.setitem(sys.modules, "openai", mock_openai)

    with patch("hiron.embeddings.generator.get_settings") as mock_get_settings:
        mock_get_settings.return_value.is_production = False

        result = generator.generate_embedding("Test Fallback")

        assert len(result.embedding) == EMBEDDING_DIMENSION
        assert result.input_tokens == 0
        assert result.total_tokens == 0
        assert result.status == "error"
        assert result.is_fallback is True
        assert result.error_type == "Exception"


def test_embedding_generator_production_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify generator propagates exceptions without fallback in production."""
    generator = EmbeddingGenerator()
    generator.openai_api_key = "test_key"

    class FakeOpenAIError(Exception):
        pass

    mock_openai = MagicMock()
    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = FakeOpenAIError("Terminal Production Error")
    mock_openai.OpenAI.return_value = mock_client

    import sys
    monkeypatch.setitem(sys.modules, "openai", mock_openai)

    with patch("hiron.embeddings.generator.get_settings") as mock_get_settings:
        mock_get_settings.return_value.is_production = True

        with pytest.raises(FakeOpenAIError):
            generator.generate_embedding("Test Production Fail")

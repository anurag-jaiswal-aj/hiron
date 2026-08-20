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


async def test_embedding_generator_gemini_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify generator correctly formats Gemini success into EmbeddingGenerationResult."""
    generator = EmbeddingGenerator()
    generator.gemini_api_key = "test_key"
    sample_text = "Senior Python Engineer"

    # Mock the embedding response structure
    mock_response = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1] * EMBEDDING_DIMENSION
    mock_response.embeddings = [mock_embedding]

    from unittest.mock import AsyncMock

    mock_client_instance = MagicMock()
    mock_client_instance.aio.models.embed_content = AsyncMock(return_value=mock_response)

    mock_count_response = MagicMock()
    mock_count_response.total_tokens = 42
    mock_client_instance.aio.models.count_tokens = AsyncMock(return_value=mock_count_response)

    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client_instance

    import sys

    monkeypatch.setitem(sys.modules, "google.genai", mock_genai)
    monkeypatch.setitem(sys.modules, "google", MagicMock(genai=mock_genai))

    # We also mock get_settings to avoid production missing key errors for basic tests
    with patch("hiron.embeddings.generator.get_settings") as mock_get_settings:
        mock_get_settings.return_value.is_production = False
        result = await generator.generate_embedding(sample_text)

    assert len(result.embedding) == EMBEDDING_DIMENSION
    assert result.status == "success"
    assert result.is_fallback is False
    assert result.error_type is None

    # Verify client was instantiated with API key
    mock_genai.Client.assert_called_once_with(api_key="test_key")

    # Verify the model parameters
    call_kwargs = mock_client_instance.aio.models.embed_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-embedding-2"
    assert call_kwargs["contents"] == sample_text

    # Verify EmbedContentConfig was constructed with correct args
    mock_genai.types.EmbedContentConfig.assert_called_once_with(
        output_dimensionality=EMBEDDING_DIMENSION,
        task_type="RETRIEVAL_DOCUMENT",
    )


async def test_embedding_generator_fallback_non_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify generator falls back to mock vector when not in production and Gemini fails."""
    generator = EmbeddingGenerator()
    generator.gemini_api_key = "test_key"

    mock_genai = MagicMock()
    mock_client = MagicMock()
    mock_client.aio.models.embed_content = __import__("unittest.mock").mock.AsyncMock(
        side_effect=Exception("Gemini API Error")
    )
    mock_genai.Client.return_value = mock_client

    import sys

    monkeypatch.setitem(sys.modules, "google.genai", mock_genai)
    monkeypatch.setitem(sys.modules, "google", MagicMock(genai=mock_genai))

    with patch("hiron.embeddings.generator.get_settings") as mock_get_settings:
        mock_get_settings.return_value.is_production = False

        result = await generator.generate_embedding("Test Fallback")

        assert len(result.embedding) == EMBEDDING_DIMENSION
        assert result.input_tokens == 0
        assert result.total_tokens == 0
        assert result.status == "error"
        assert result.is_fallback is True
        assert result.error_type == "Exception"


async def test_embedding_generator_production_failure_no_key() -> None:
    """Verify generator fails explicitly when missing API key in production."""
    generator = EmbeddingGenerator()
    generator.gemini_api_key = None

    with patch("hiron.embeddings.generator.get_settings") as mock_get_settings:
        mock_get_settings.return_value.is_production = True

        with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
            await generator.generate_embedding("Test")


async def test_embedding_generator_production_failure_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify generator propagates exceptions without fallback in production."""
    generator = EmbeddingGenerator()
    generator.gemini_api_key = "test_key"

    class FakeGeminiError(Exception):
        pass

    mock_genai = MagicMock()
    mock_client = MagicMock()
    mock_client.aio.models.embed_content = __import__("unittest.mock").mock.AsyncMock(
        side_effect=FakeGeminiError("Terminal Production Error")
    )
    mock_genai.Client.return_value = mock_client

    import sys

    monkeypatch.setitem(sys.modules, "google.genai", mock_genai)
    monkeypatch.setitem(sys.modules, "google", MagicMock(genai=mock_genai))

    with patch("hiron.embeddings.generator.get_settings") as mock_get_settings:
        mock_get_settings.return_value.is_production = True

        with pytest.raises(FakeGeminiError):
            await generator.generate_embedding("Test Production Fail")


async def test_embedding_generator_invalid_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify generator fails explicitly if provider returns incorrect dimensions."""
    generator = EmbeddingGenerator()
    generator.gemini_api_key = "test_key"

    mock_response = MagicMock()
    mock_embedding = MagicMock()
    # Mock returning 5 dimensions instead of 768
    mock_embedding.values = [0.1] * 5
    mock_response.embeddings = [mock_embedding]

    mock_client_instance = MagicMock()
    mock_client_instance.aio.models.embed_content = __import__("unittest.mock").mock.AsyncMock(
        return_value=mock_response
    )

    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client_instance

    import sys

    monkeypatch.setitem(sys.modules, "google.genai", mock_genai)
    monkeypatch.setitem(sys.modules, "google", MagicMock(genai=mock_genai))

    with patch("hiron.embeddings.generator.get_settings") as mock_get_settings:
        mock_get_settings.return_value.is_production = True

        with pytest.raises(ValueError, match=f"Expected {EMBEDDING_DIMENSION} dimensions, got 5"):
            await generator.generate_embedding("Test Dimensions Fail")

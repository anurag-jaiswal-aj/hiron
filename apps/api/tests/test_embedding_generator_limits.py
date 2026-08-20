from hiron.embeddings.generator import EmbeddingGenerator


async def test_embedding_generator_char_limits(monkeypatch):
    # Ensure we use mock vector for the test so we don't hit Gemini API rate limits
    monkeypatch.setenv("GEMINI_API_KEY", "")

    generator = EmbeddingGenerator()

    # Helper to check if text was truncated to 30000 chars
    async def assert_truncated_to_max(original_text, max_chars=30000):
        original_hash_method = generator.compute_source_text_hash

        captured_text = []
        def mock_hash(text):
            captured_text.append(text)
            return original_hash_method(text)

        monkeypatch.setattr(generator, "compute_source_text_hash", mock_hash)

        # We need to mock get_settings as well for non-production error suppression
        from unittest.mock import patch
        with patch("hiron.embeddings.generator.get_settings") as mock_get_settings:
            mock_get_settings.return_value.is_production = False
            await generator.generate_embedding(original_text)

        # Check chars of the captured text
        final_text = captured_text[0]
        assert len(final_text) <= max_chars

        # Clean up patch
        monkeypatch.setattr(generator, "compute_source_text_hash", original_hash_method)

    # 1. Normal English text
    normal_text = "This is a normal English sentence representing a candidate resume."
    await assert_truncated_to_max(normal_text)

    # 2. Long text (exceeding 30000 chars)
    long_text = "hello " * 10000
    await assert_truncated_to_max(long_text)

    # 3. Non-Latin text
    non_latin = "こんにちは世界 " * 8000
    await assert_truncated_to_max(non_latin)

    # 4. Dense/symbolic text
    dense_text = "!@#$%^&*()_+" * 5000
    await assert_truncated_to_max(dense_text)

    # 5. Boundary-sized input (exactly 30000 chars)
    boundary_text = "a" * 30000
    await assert_truncated_to_max(boundary_text)

import pytest
import tiktoken
from hiron.embeddings.generator import EmbeddingGenerator

def test_embedding_generator_token_limits(monkeypatch):
    # Ensure we use mock vector for the test so we don't hit OpenAI API rate limits
    monkeypatch.setenv("OPENAI_API_KEY", "")
    
    generator = EmbeddingGenerator()
    encoding = tiktoken.get_encoding("cl100k_base")
    
    # Helper to check if text was truncated to 8190 tokens
    def assert_truncated_to_max(original_text, max_t=8190):
        # We need to capture the text that actually gets hashed/embedded
        # To do this, we can monkeypatch compute_source_text_hash to just return the length of the tokens
        original_hash_method = generator.compute_source_text_hash
        
        captured_text = []
        def mock_hash(text):
            captured_text.append(text)
            return original_hash_method(text)
            
        monkeypatch.setattr(generator, "compute_source_text_hash", mock_hash)
        
        generator.generate_embedding(original_text)
        
        # Check tokens of the captured text
        final_text = captured_text[0]
        final_tokens = encoding.encode(final_text)
        assert len(final_tokens) <= max_t
        
        # Clean up patch
        monkeypatch.setattr(generator, "compute_source_text_hash", original_hash_method)

    # 1. Normal English text
    normal_text = "This is a normal English sentence representing a candidate resume."
    assert_truncated_to_max(normal_text)
    
    # 2. Long text (exceeding 8192 tokens)
    # "hello " is 1 token. 10000 times = 10000 tokens.
    long_text = "hello " * 10000
    assert_truncated_to_max(long_text)
    
    # 3. Non-Latin text
    non_latin = "こんにちは世界 " * 4000  # CJK characters, usually >1 token per char
    assert_truncated_to_max(non_latin)
    
    # 4. Dense/symbolic text
    dense_text = "!@#$%^&*()_+" * 5000
    assert_truncated_to_max(dense_text)

    # 5. Boundary-sized input (exactly 8190 tokens)
    boundary_text = "word " * 8190
    assert_truncated_to_max(boundary_text)

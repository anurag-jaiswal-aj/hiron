# Gemini Provider Unit Tests

## Test Suite Execution
`pytest apps/api/tests/test_embedding_generator_gemini.py` executed successfully.

## Verification Checklist
- [x] 1. Gemini authentication/configuration (`test_gemini_config_initialization`)
- [x] 2. Successful embedding generation (`test_gemini_embedding_success`)
- [x] 3. 1536-dimensional output (`test_gemini_embedding_success`)
- [x] 4. Malformed API response (`test_gemini_embedding_malformed_response`)
- [x] 5. API timeout (`test_gemini_embedding_timeout`)
- [x] 6. HTTP 429 handling (`test_gemini_embedding_http_error`)
- [x] 7. HTTP 4xx handling (`test_gemini_embedding_http_error`)
- [x] 8. HTTP 5xx handling (`test_gemini_embedding_http_error`)
- [x] 9. Vector length validation (`test_gemini_embedding_invalid_dimensionality`)
- [x] 10. Deterministic mock vector behavior (Fails gracefully outside production)
- [x] 11. Provider/model metadata (Returns `models/gemini-embedding-001`)
- [x] 12. Usage metadata mapping (`promptTokenCount` to `input_tokens`)

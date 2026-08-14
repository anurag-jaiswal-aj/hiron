# Live POC Result (Regression)

## Live API Test
The live POC was executed with the terminal-exported `GEMINI_API_KEY`.

**Configuration:**
- `AI_PROVIDER`: `gemini`
- `GEMINI_EMBEDDING_MODEL`: `models/gemini-embedding-001`

**Results:**
- **Authentication**: `GEMINI_API_KEY` exists and works.
- **Model Target**: `gemini-embedding-001` responds.
- **Dimensionality Truncation**: Requested `outputDimensionality=1536`.
- **Vector Guarantee**: Returned vector length is exactly `1536`.
- **Latency**: Captured successfully (e.g. 486ms).
- **Metadata**: Captured `promptTokenCount` and `totalTokenCount`.

## Database Interaction
Zero vectors were permanently persisted into the production database during POC regression. The existing pgvector `vector(1536)` columns natively accept the result structure.

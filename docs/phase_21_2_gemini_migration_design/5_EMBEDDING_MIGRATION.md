# 5. Embedding Migration

## Current Architecture
`EmbeddingGenerator` calls `openai.embeddings.create(model="text-embedding-3-small", input=text)`.
Database schema: `embedding vector(1536)`.

## Target Architecture
Call `gemini-embedding-001` via REST API using `outputDimensionality: 1536`.

### API Payload
```json
{
  "model": "models/gemini-embedding-001",
  "content": {"parts": [{"text": "..."}]},
  "outputDimensionality": 1536
}
```

### Compatibility Check
Live POC (Phase 21.1) proved that `gemini-embedding-001` successfully returns exactly 1536 dimensions. 
No database migration is required. HNSW similarity search logic will continue working natively.

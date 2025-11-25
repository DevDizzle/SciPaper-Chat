# GCP-native RAG refactor design note

## Goals
- Eliminate LangChain/FAISS dependency issues by leaning on first-party Google services.
- Use Vertex AI for embeddings, vector search, and generation.
- Keep a thin FastAPI layer suitable for Cloud Run.

## Data flow
1. **Upload** (`/upload`): accept PDF → parse with pypdf → chunk → embed via Vertex AI → upsert to Vertex AI Vector Search (namespaced by `paper_id`).
2. **Summaries**: initial summary generated with Gemini and stored in Firestore for quick retrieval.
3. **Query** (`/query`): ADK-style agent retrieves top-k chunk IDs from Vector Search, fetches chunk text from Firestore, combines with chat history from Firestore, and calls Gemini for a grounded answer.
4. **Summary retrieval** (`/summary/{paper_id}`): read the latest persisted summary from Firestore.

## Components
- `ingestion/pipeline.py`: orchestrates PDF parsing, chunking, embeddings, Vector Search upserts, and summary creation.
- `services/vector_search.py`: wraps Vertex AI Vector Search endpoint for upsert + query using namespace filters on `paper_id`.
- `services/embedding.py`: Vertex AI `text-embedding-004` helper.
- `services/storage.py`: Firestore storage for chat messages, chunk text, and summaries.
- `agents/adk_agent.py`: lightweight agent that mirrors ADK patterns—retrieves context then calls Gemini.
- `main.py`: FastAPI endpoints for upload, query, summary, and health.
- `config.py`: centralizes environment-based configuration (project, region, model IDs, index IDs, bucket).

## Indexing strategy
- **Single global index** in Vertex AI Vector Search with namespace restricts: each chunk upsert includes `paper_id` in restricts to isolate queries.
- **Only IDs + restricts in the index**: Vector Search stores the embedding and datapoint ID (`{paper_id}-{chunk_index}`) with `paper_id` restricts; chunk text lives solely in Firestore to avoid oversized metadata and align with Google guidance.

## Storage decisions
- **Firestore**: chosen for lightweight session + summary metadata; Collections: `sessions/{session_id}/messages`, `summaries/{paper_id}`, and `paper_chunks` documents keyed by the Vector Search datapoint ID containing chunk text + metadata.
- **GCS**: optional PDF storage; ingestion operates on uploaded bytes regardless.

## Models
- **Embeddings**: `text-embedding-004` (configurable via `EMBEDDING_MODEL`).
- **Generation**: `gemini-1.5-flash-001` (configurable via `GENERATION_MODEL`).

## Deployment considerations
- Environment variables supply project/region, bucket, and Vector Search identifiers.
- Dependencies minimized to Google client libraries + FastAPI; pinned via `pip-compile` to reduce resolver churn in Cloud Run builds.
- Entry command: `uvicorn main:app --host 0.0.0.0 --port 8080`.

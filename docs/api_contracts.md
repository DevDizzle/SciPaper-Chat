# API Contracts and UI Plan

The FastAPI service exposes a clean REST surface that UI clients (Streamlit, React, etc.) can consume without embedding UI logic in the production container.

## Endpoints

### `GET /health`
- **Purpose:** Liveness probe for Cloud Run and monitoring.
- **Response:** `{ "status": "ok" }`

### `POST /session`
- **Purpose:** Obtain a Firestore-backed session ID for chat history persistence.
- **Response:** `{ "session_id": "<uuid>" }`

### `POST /analyze`
- **Purpose:** Ingest a paper, build embeddings, and generate the running summary.
- **Input:**
  - Multipart form with either:
    - `file`: PDF upload (binary)
    - `arxiv_id`: string ArXiv identifier
- **Response:**
  ```json
  {
    "status": "Processed <n> chunks.",
    "summary": "<running summary>",
    "session_id": "<uuid>"
  }
  ```
  The session ID returned here can be reused for chat persistence.

### `POST /chat`
- **Purpose:** Ask a grounded question against the current vector store.
- **Input (JSON):** `{ "message": "<user question>", "session_id": "<uuid>" }`
- **Response:** `{ "response": "<grounded answer>" }`

## UI options

### Option A: Streamlit (demo/internal)
- Build a small Streamlit app (separate repo/service) that:
  1. Calls `POST /session` on startup to get a session ID.
  2. Lets the user upload a PDF or enter an ArXiv ID and sends it to `POST /analyze`.
  3. Displays the returned summary.
  4. Renders a chat input that calls `POST /chat` with the session ID and shows the responses.
- Dependencies live in a separate `requirements.txt` for the Streamlit project; do **not** install into the backend container.

### Option B: React (SPA)
- Create a Vite/Next.js SPA that:
  1. Calls `POST /session` when the page loads.
  2. Uses a file input to upload PDFs or a text input for ArXiv IDs and sends a multipart form to `POST /analyze`.
  3. Shows the running summary from the response.
  4. Provides a chat box that sends JSON to `POST /chat` and renders the streaming/returned answer.
- Configure CORS to allow the frontend origin; the backend currently allows all origins for ease of local development.

## Notes
- Firestore-backed session persistence and the RAG pipeline are unchanged from the original design.
- Gradio is no longer part of the production image; it can be added to a local dev environment via `requirements-dev.txt` if desired.

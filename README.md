# Master Build Reference: Scientific Paper Analyzer

## Project Context

A cloud-deployed, conversational AI tool that helps students and faculty analyze scientific papers. It uses Retrieval-Augmented Generation (RAG) to provide grounded answers and summaries from PDF uploads.

### Target Architecture

- **Compute:** Google Cloud Run (Serverless, stateless container)
- **Frontend:** Gradio (Python-based web UI)
- **AI Backend:** Google Vertex AI (Gemini 1.5 Flash) & Vertex AI Embeddings
- **State Management (Critical):** Google Firestore (NoSQL) for session persistence

---

## 1. Requirements & Constraints

Extracted from `ProjectRequirements_Final.pdf` and `TestCaseAssignmentFinal.pdf`.

### Functional Constraints

- **UR-1.1 (PDF Upload):** The system must accept PDF files.
- **UR-1.3 (Grounded Q&A):** Answers must be derived from the document context (RAG).
- **UR-1.2 (Summarization):** Must generate a concise running summary upon upload.

### Non-Functional Constraints

- **TC-NFR6 (Session Persistence):**  
  The system must maintain dialogue continuity across user interactions.  
  - **Challenge:** Cloud Run is stateless.  
  - **Solution:** Store chat history in Firestore keyed by `session_id`.

- **TC-NFR5 (Usability):**  
  Interface must be accessible to non-technical users (Gradio satisfies this).

- **Performance:**  
  Average response time should be ≤ 3 seconds (Gemini Flash is optimized for this).

---

## 2. Implementation Specifications

### 2.1 Dependencies (`requirements.txt`)

Essential libraries for the Cloud Run environment:

```txt
fastapi==0.109.0
uvicorn==0.27.0
gradio==4.16.0
langchain==0.1.4
langchain-google-vertexai==0.0.5
langchain-community==0.0.16
google-cloud-firestore==2.14.0
faiss-cpu==1.7.4
pypdf==4.0.1
arxiv==2.1.0
pydantic==2.6.0

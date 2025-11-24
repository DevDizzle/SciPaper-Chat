"""ADK-style agent that orchestrates retrieval and grounded generation."""
from __future__ import annotations

from typing import List, Optional

import vertexai
from vertexai.generative_models import GenerativeModel, Part

import config
from services import embedding, storage, vector_search


def _init_vertex() -> None:
    vertexai.init(project=config.PROJECT_ID, location=config.REGION)


def build_prompt(question: str, contexts: List[str], history: List[str]) -> str:
    context_block = "\n\n".join(contexts) if contexts else "No context retrieved."
    history_block = "\n".join(history)
    return f"""
You are an assistant answering questions about a single scientific paper.
Use only the provided context and history. If the answer is not present, say you don't know.

Context:
{context_block}

Conversation history:
{history_block}

Question: {question}

Respond concisely for a technical reader and avoid speculation.
"""


class PaperRAGAgent:
    """Minimal agent orchestrated in code to align with Google ADK patterns."""

    def __init__(self) -> None:
        _init_vertex()
        self.model = GenerativeModel(config.GENERATION_MODEL)

    def _search(self, question: str, paper_id: str, top_k: int) -> List[str]:
        query_embedding = embedding.embed_texts([question])[0]
        results = vector_search.query(
            query_vector=query_embedding,
            paper_id=paper_id,
            top_k=top_k,
        )
        contexts: List[str] = []
        for result in results:
            metadata = result.get("metadata", {})
            text = metadata.get("text") or metadata.get("chunk")
            if text:
                contexts.append(text)
        return contexts

    def answer_question(
        self, *, paper_id: str, session_id: Optional[str], question: str, top_k: int
    ) -> str:
        history = storage.load_chat_history(session_id)
        contexts = self._search(question, paper_id, top_k)
        prompt = build_prompt(question, contexts, history)

        response = self.model.generate_content([Part.from_text(prompt)])
        text = response.text if hasattr(response, "text") else str(response)

        if session_id:
            storage.save_chat_history(session_id, "user", question)
            storage.save_chat_history(session_id, "ai", text)
        return text

"""ADK-style agent that orchestrates retrieval and grounded generation."""
from __future__ import annotations

from typing import Dict, List, Optional

import vertexai
from vertexai.generative_models import GenerativeModel, Part

import config
from services import embedding, storage, vector_search


def _init_vertex() -> None:
    vertexai.init(project=config.PROJECT_ID, location=config.REGION)


def build_prompt(question: str, contexts: List[Dict[str, str]], history: List[str]) -> str:
    """Builds a prompt with context from multiple papers and new citation rules."""
    if contexts:
        context_parts = []
        for chunk in contexts:
            # The chunk dict from Firestore contains 'paper_id' and 'text'
            context_parts.append(f"--- CONTEXT from paper {chunk.get('paper_id', 'unknown')} ---\n{chunk.get('text', '')}")
        context_block = "\n\n".join(context_parts)
    else:
        context_block = "No context retrieved."

    history_block = "\n".join(history)

    return f"""
You are an expert scientific assistant answering questions about a collection of papers.
Use ONLY the provided context to answer.

**Citation Rule:**
The context is sourced from multiple papers, identified by their arXiv ID.
You MUST cite your claims by referencing the paper ID found with the information.
Format citations as [from <paper_id>].
Example: "The study found that Bayes error could be optimized [from 2305.10601v1]."

Context:
{context_block}

Conversation history:
{history_block}

Question: {question}

Respond concisely for a technical reader. If the answer is not in the context, say you don't know.
"""


class PaperRAGAgent:
    """Minimal agent orchestrated in code to align with Google ADK patterns."""

    def __init__(self) -> None:
        _init_vertex()
        self.model = GenerativeModel(config.GENERATION_MODEL)

    def _search(self, question: str, paper_ids: list[str], top_k: int) -> List[Dict[str, str]]:
        """Search across multiple paper IDs and return chunk metadata."""
        query_embedding = embedding.embed_texts([question])[0]
        results = vector_search.query(
            query_vector=query_embedding,
            paper_ids=paper_ids,
            top_k=top_k,
        )
        chunk_ids = [r["id"] for r in results if r.get("id")]
        chunk_map = storage.fetch_chunks(chunk_ids)
        # Return the full chunk dictionary, which includes the source paper_id
        return [chunk_map[cid] for cid in chunk_ids if cid in chunk_map]

    def answer_question(
        self, *, paper_ids: list[str], session_id: Optional[str], question: str, top_k: int
    ) -> str:
        history = storage.load_chat_history(session_id)
        contexts = self._search(question, paper_ids, top_k)
        prompt = build_prompt(question, contexts, history)

        response = self.model.generate_content([Part.from_text(prompt)])
        text = response.text if hasattr(response, "text") else str(response)

        if session_id:
            storage.save_chat_history(session_id, "user", question)
            storage.save_chat_history(session_id, "ai", text)
        return text

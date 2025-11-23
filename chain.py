"""Core RAG and persistence logic for the Scientific Paper Analyzer."""

from datetime import datetime
from typing import List, Optional, Tuple

from google.cloud import firestore
from langchain_google_vertexai import VertexAIEmbeddings, ChatVertexAI
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, ArxivLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from pydantic import BaseModel, Field

EMBEDDING_MODEL = "text-embedding-004"
LLM_MODEL = "gemini-1.5-flash-001"


# Initialize shared clients and state.
db = firestore.Client()
embedder = VertexAIEmbeddings(model_name=EMBEDDING_MODEL)
llm = ChatVertexAI(model_name=LLM_MODEL, temperature=0.2)
vector_store: Optional[FAISS] = None


def save_chat_history(session_id: Optional[str], user_query: str, ai_response: str) -> None:
    """Persist a single user/AI exchange to Firestore (TC-NFR6)."""
    if not session_id:
        return

    messages_ref = db.collection("sessions").document(session_id).collection("messages")
    messages_ref.add({
        "role": "user",
        "content": user_query,
        "timestamp": datetime.utcnow(),
    })
    messages_ref.add({
        "role": "ai",
        "content": ai_response,
        "timestamp": datetime.utcnow(),
    })


def get_chat_history(session_id: Optional[str]) -> str:
    """Return the last 10 chat messages ordered by time."""
    if not session_id:
        return ""

    messages = (
        db.collection("sessions")
        .document(session_id)
        .collection("messages")
        .order_by("timestamp")
        .limit(10)
        .stream()
    )
    history_lines = [
        f"{message.to_dict()['role'].upper()}: {message.to_dict()['content']}"
        for message in messages
    ]
    return "\n".join(history_lines)


class DocumentSummary(BaseModel):
    """Structured running summary similar to the original notebook design."""

    running_summary: str = Field(
        "", description="Running description of the document; refine and extend over time."
    )
    main_ideas: List[str] = Field(
        default_factory=list,
        description="Most important information from the document (max 3 items).",
    )
    loose_ends: List[str] = Field(
        default_factory=list,
        description="Open questions to revisit (max 3 items).",
    )


def _load_documents(file_path: Optional[str], arxiv_id: Optional[str]) -> List:
    if file_path:
        return PyPDFLoader(file_path).load()
    if arxiv_id:
        return ArxivLoader(query=arxiv_id).load()
    return []


def _generate_running_summary(split_docs: List) -> DocumentSummary:
    """Iteratively update a structured running summary across chunks."""

    parser = PydanticOutputParser(pydantic_object=DocumentSummary)
    summary_prompt = ChatPromptTemplate.from_template(
        """
You are updating a running knowledge base for a scientific paper. Maintain continuity and precision for a technical reader.

Current state:
- running_summary: {running_summary}
- main_ideas: {main_ideas}
- loose_ends: {loose_ends}

Guidance:
- Keep running_summary concise but dense.
- main_ideas: up to 3 bullet-like facts.
- loose_ends: up to 3 open questions or details to revisit.
- Do not drop useful information already present.
- Use the provided format instructions exactly.

{format_instructions}

Incorporate the following new chunk:
{chunk_text}
"""
    )

    chain = summary_prompt.partial(
        format_instructions=parser.get_format_instructions()
    ) | llm | parser

    state = DocumentSummary()
    for doc in split_docs:
        state = chain.invoke(
            {
                "running_summary": state.running_summary,
                "main_ideas": state.main_ideas,
                "loose_ends": state.loose_ends,
                "chunk_text": doc.page_content,
            }
        )
    return state


def process_document(file_path: Optional[str] = None, arxiv_id: Optional[str] = None) -> Tuple[str, str]:
    """Ingest a document (UR-1.1), build the vector store, and summarize (UR-1.2)."""
    global vector_store

    docs = _load_documents(file_path, arxiv_id)
    if not docs:
        return "No document found.", ""

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    split_docs = text_splitter.split_documents(docs)

    structured_summary = _generate_running_summary(split_docs)
    summary = "\n".join(
        filter(
            None,
            [
                structured_summary.running_summary.strip(),
                "Main ideas:",
                *[f"- {idea}" for idea in structured_summary.main_ideas],
                "Loose ends:",
                *[f"- {end}" for end in structured_summary.loose_ends],
            ],
        )
    )

    vector_store = FAISS.from_documents(split_docs, embedder)
    return f"Processed {len(split_docs)} chunks.", summary


def answer_question(message: str, history: List, session_id: Optional[str]) -> str:
    """Answer a question using RAG with chat history persistence (UR-1.3, TC-NFR6)."""
    del history  # Managed via Firestore instead of Gradio's local state.

    global vector_store
    if not vector_store:
        return "Please upload a document first."

    retriever = vector_store.as_retriever()
    context = "\n\n".join([
        document.page_content for document in retriever.get_relevant_documents(message)
    ])

    db_history = get_chat_history(session_id)
    prompt = ChatPromptTemplate.from_template(
        """
You are a document assistant. Answer strictly from the retrieved context and history. If the answer is not in the context, say you don't know.

Context:
{context}

Chat History:
{chat_history}

Question: {question}

Guidelines:
- Be concise and precise for a technical reader.
- Cite the relevant snippet briefly inline (e.g., [source]).
- Do not invent information or external knowledge.

Answer:
"""
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke(
        {"context": context, "chat_history": db_history, "question": message}
    )

    save_chat_history(session_id, message, response)
    return response

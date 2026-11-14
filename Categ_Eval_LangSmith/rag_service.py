"""Reusable hybrid RAG service for the SuperGlasses support assistant."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone

PROJECT_DIR = Path(__file__).resolve().parent
KNOWLEDGE_BASE_PATH = PROJECT_DIR / "kb_eyeglass_01.json"

RAG_PROMPT = """You are a customer support specialist for SuperGlasses, an online eyeglass shop.
Use the context below to help resolve the customer's question.

If the context doesn't contain the answer, state that you don't have that information rather than guessing.
Be concise and practical: state the likely cause and the next step the agent should take.

Context:
{context}

Customer issue: {question}

Support guidance:"""


class ConfigurationError(RuntimeError):
    """Raised when required service configuration is unavailable."""


@dataclass(frozen=True)
class Source:
    """A retrieved knowledge-base source returned to API clients."""

    title: str
    content: str
    doc_type: str
    category: str
    ticket_id: str | None = None


@dataclass(frozen=True)
class SearchResult:
    """The generated answer and its supporting sources."""

    answer: str
    sources: list[Source]


class HybridRagService:
    """Hybrid semantic/keyword retrieval with an LLM-generated answer."""

    def __init__(self, knowledge_base_path: Path = KNOWLEDGE_BASE_PATH) -> None:
        load_dotenv(PROJECT_DIR / ".env")
        self.knowledge_base_path = knowledge_base_path
        self._validate_environment()
        self.llm = ChatOpenAI(model="gpt-4.1-mini")
        self.rag_prompt_template = PromptTemplate.from_template(RAG_PROMPT)
        self.ensemble_retriever = self._create_retriever()

    def _validate_environment(self) -> None:
        """Ensure credentials and remote service settings are configured."""
        required_values = (
            "OPENAI_API_KEY",
            "PINECONE_API_KEY",
            "PINECONE_INDEX_NAME",
            "PINECONE_NAMESPACE",
        )
        missing = [name for name in required_values if not os.environ.get(name)]
        if missing:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    def _create_retriever(self) -> Any:
        """Initialize Pinecone and BM25 retrievers, then fuse them."""
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", dimensions=512
        )
        pinecone = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        index = pinecone.Index(os.environ["PINECONE_INDEX_NAME"])
        vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings,
            namespace=os.environ["PINECONE_NAMESPACE"],
        )
        vector_retriever = vector_store.as_retriever(search_kwargs={"k": 3})

        raw_docs = self._load_documents()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=150,
            chunk_overlap=50,
            add_start_index=True,
        )
        docs = splitter.split_documents(raw_docs)
        bm25_retriever = BM25Retriever.from_documents(docs)
        bm25_retriever.k = 3

        # EnsembleRetriever lives in langchain-classic for this project.
        from langchain_classic.retrievers import EnsembleRetriever

        return EnsembleRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            weights=[0.5, 0.5],
        )

    def _load_documents(self) -> list[Document]:
        """Load the local knowledge base used by the BM25 retriever."""
        if not self.knowledge_base_path.exists():
            raise ConfigurationError(
                f"Knowledge base not found at {self.knowledge_base_path}"
            )
        try:
            with self.knowledge_base_path.open(encoding="utf-8") as file:
                knowledge_base = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(
                f"Could not load the knowledge base: {exc}"
            ) from exc

        return [
            Document(
                page_content=entry["content"],
                metadata=entry.get("metadata", {}),
            )
            for entry in knowledge_base
        ]

    def retrieve(self, question: str) -> list[Document]:
        """Run the hybrid retriever for a customer question."""
        return self.ensemble_retriever.invoke(question)

    def generate_answer(self, question: str, documents: list[Document]) -> str:
        """Generate a grounded support answer from retrieved documents."""
        context = "\n\n".join(document.page_content for document in documents)
        prompt = self.rag_prompt_template.invoke(
            {"question": question, "context": context}
        )
        response = self.llm.invoke(prompt)
        return str(response.content).strip()

    def search(self, question: str) -> SearchResult:
        """Retrieve supporting context and generate a grounded answer."""
        documents = self.retrieve(question)
        answer = self.generate_answer(question, documents)
        sources = [
            Source(
                title=str(document.metadata.get("title", "Untitled source")),
                content=document.page_content,
                doc_type=str(document.metadata.get("doc_type", "unknown")),
                category=str(document.metadata.get("category", "unknown")),
                ticket_id=(
                    str(document.metadata["ticket_id"])
                    if document.metadata.get("ticket_id")
                    else None
                ),
            )
            for document in documents
        ]
        return SearchResult(answer=answer, sources=sources)


@lru_cache(maxsize=1)
def get_rag_service() -> HybridRagService:
    """Return a lazily initialized shared service instance."""
    return HybridRagService()

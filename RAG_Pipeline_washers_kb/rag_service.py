"""
Hybrid RAG service for MegaWasher by Louis C Trevino 2026

Reusable core of the hybrid (semantic / BM25 keyword) RAG pipeline.
All heavy resources (Pinecone index, BM25 index, LLM) are built once in
HybridRAG.__init__ and reused across queries, so the same instance can serve
both the CLI (retriever_hybrid.py) and the FastAPI backend (api.py).
"""
import json
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
KB_PATH = BASE_DIR / "kb_washers_01.json"

load_dotenv(BASE_DIR / ".env")

TOP_K = 3
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 512
LLM_MODEL = "gpt-4.1-mini"

RAG_TEMPLATE = """You are a customer support specialist for MegaWasher, a washing machine company.
Use the context below to help resolve the customer's question.

If the context doesn't contain the answer, state that you don't have that information rather than guessing.
Be concise and practical: state the likely cause and the next step the agent should take.

Context:
{context}

Customer issue: {question}

Support guidance:"""


@dataclass
class RAGResult:
    question: str
    answer: str
    citations: list[Document] = field(default_factory=list)


class HybridRAG:
    """Hybrid semantic (Pinecone) + keyword (BM25) retriever with LLM answer generation."""

    def __init__(self, kb_path: Path = KB_PATH, top_k: int = TOP_K):
        # Semantic retriever (Pinecone)
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, dimensions=EMBEDDING_DIMS)
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        index = pc.Index(os.environ["PINECONE_INDEX_NAME"])
        vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings,
            namespace=os.environ["PINECONE_NAMESPACE"],
        )
        self.vector_retriever = vector_store.as_retriever(search_kwargs={"k": top_k})

        # Keyword retriever (BM25) over the same chunks used at ingestion
        with open(kb_path, encoding="utf-8") as f:
            kb = json.load(f)
        raw_docs = [
            Document(page_content=entry["content"], metadata=entry["metadata"])
            for entry in kb
        ]
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=150, chunk_overlap=50, add_start_index=True
        )
        self.bm25_retriever = BM25Retriever.from_documents(splitter.split_documents(raw_docs))
        self.bm25_retriever.k = top_k

        # Doc fusion: equal weight to semantic and keyword search
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[self.vector_retriever, self.bm25_retriever],
            weights=[0.5, 0.5],
        )

        self.llm = ChatOpenAI(model=LLM_MODEL)
        self.prompt = PromptTemplate.from_template(RAG_TEMPLATE)

    def retrieve(self, question: str) -> list[Document]:
        return self.ensemble_retriever.invoke(question)

    def ask(self, question: str) -> RAGResult:
        docs = self.retrieve(question)
        context = "\n\n".join(doc.page_content for doc in docs)
        prompt = self.prompt.invoke({"question": question, "context": context})
        response = self.llm.invoke(prompt)
        return RAGResult(question=question, answer=response.content, citations=docs)

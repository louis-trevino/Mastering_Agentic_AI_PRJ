"""
MegaWasher RAG REST API by Louis C Trevino 2026

FastAPI backend exposing the hybrid RAG pipeline (rag_service.py).

Run:  uv run uvicorn api:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag_service import HybridRAG

logger = logging.getLogger("megawasher.api")

SNIPPET_CHARS = 300


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000,
                          examples=["My front load washer door won't open. What can I do?"])


class Citation(BaseModel):
    ticket_id: str | None = None
    title: str
    doc_type: str
    product_area: str
    product_type: str | None = None
    snippet: str


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation]


class HealthResponse(BaseModel):
    status: str
    rag_ready: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build the RAG pipeline once at startup (Pinecone + BM25 + LLM clients).
    app.state.rag = await run_in_threadpool(HybridRAG)
    yield


app = FastAPI(title="MegaWasher RAG API", version="0.1.0", lifespan=lifespan)

# Allow the Vite dev server (and any extra origins set in CORS_ORIGINS, comma-separated).
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", rag_ready=getattr(app.state, "rag", None) is not None)


@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question must not be blank.")
    try:
        # LangChain calls are blocking; keep the event loop free.
        result = await run_in_threadpool(app.state.rag.ask, question)
    except Exception:
        logger.exception("RAG query failed")
        raise HTTPException(status_code=502, detail="The RAG service failed to answer. Please try again.")

    citations = [
        Citation(
            ticket_id=d.metadata.get("ticket_id"),
            title=d.metadata.get("title", "Untitled"),
            doc_type=d.metadata.get("doc_type", "unknown"),
            product_area=d.metadata.get("product_area", "unknown"),
            product_type=d.metadata.get("product_type"),
            snippet=d.page_content[:SNIPPET_CHARS],
        )
        for d in result.citations
    ]
    return AskResponse(question=question, answer=result.answer, citations=citations)

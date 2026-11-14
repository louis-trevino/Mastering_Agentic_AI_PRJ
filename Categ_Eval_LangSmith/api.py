"""FastAPI application for the SuperGlasses hybrid RAG service."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, StringConstraints

from rag_service import (
    ConfigurationError,
    HybridRagService,
    SearchResult,
    get_rag_service,
)

Question = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=1000),
]


class SourceResponse(BaseModel):
    title: str
    content: str
    doc_type: str
    category: str
    ticket_id: str | None = None


class SearchRequest(BaseModel):
    question: Question


class SearchResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceResponse]


class HealthResponse(BaseModel):
    status: str


app = FastAPI(
    title="SuperGlasses RAG API",
    version="1.0.0",
    description="Hybrid RAG search API for SuperGlasses customer support.",
)

allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _to_response(question: str, result: SearchResult) -> SearchResponse:
    return SearchResponse(
        question=question,
        answer=result.answer,
        sources=[SourceResponse(**source.__dict__) for source in result.sources],
    )


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the API process is available."""
    return HealthResponse(status="ok")


@app.post(
    "/api/search",
    response_model=SearchResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
def search(
    request: SearchRequest,
    service: Annotated[HybridRagService, Depends(get_rag_service)],
) -> SearchResponse:
    """Search the SuperGlasses knowledge base and generate a support answer."""
    try:
        result = service.search(request.question)
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The RAG search could not be completed. Please try again.",
        ) from exc
    return _to_response(request.question, result)

"""API contract tests with a fake RAG service."""

from fastapi.testclient import TestClient

from api import app
from rag_service import SearchResult, Source


class FakeRagService:
    """Deterministic service used to test the API without network calls."""

    def search(self, question: str) -> SearchResult:
        return SearchResult(
            answer="Open the order page to view its latest status.",
            sources=[
                Source(
                    title="Order tracking",
                    content="Open your order page to view tracking.",
                    doc_type="support_ticket",
                    category="order_status",
                    ticket_id="TKT-00002",
                )
            ],
        )


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_returns_answer_and_sources(monkeypatch) -> None:
    from api import get_rag_service

    app.dependency_overrides[get_rag_service] = lambda: FakeRagService()
    try:
        response = client.post(
            "/api/search",
            json={"question": "How do I track my order?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "question": "How do I track my order?",
        "answer": "Open the order page to view its latest status.",
        "sources": [
            {
                "title": "Order tracking",
                "content": "Open your order page to view tracking.",
                "doc_type": "support_ticket",
                "category": "order_status",
                "ticket_id": "TKT-00002",
            }
        ],
    }


def test_search_rejects_blank_question() -> None:
    response = client.post("/api/search", json={"question": "  "})

    assert response.status_code == 422


def test_search_reports_configuration_errors(monkeypatch) -> None:
    from api import get_rag_service
    from rag_service import ConfigurationError

    class UnconfiguredService:
        def search(self, question: str):
            raise ConfigurationError("Missing PINECONE_API_KEY")

    app.dependency_overrides[get_rag_service] = lambda: UnconfiguredService()
    try:
        response = client.post("/api/search", json={"question": "Track my order"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "Missing PINECONE_API_KEY"

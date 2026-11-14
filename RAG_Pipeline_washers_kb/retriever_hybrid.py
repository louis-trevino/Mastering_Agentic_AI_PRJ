"""
Hybrid RAG Retrieval by Louis C Trevino 2026

Command-line front end for the hybrid (semantic / BM25 keyword) RAG pipeline.
The retrieval and generation logic lives in rag_service.py, shared with the
FastAPI backend (api.py).
"""
from rag_service import HybridRAG


def main() -> None:
    print("\n*** Welcome to MegaWasher FAQ Tool ***")
    rag = HybridRAG()

    user_query = input("\nQuery: ")
    result = rag.ask(user_query)

    print("\nCitations:")
    for doc in result.citations:
        m = doc.metadata
        print(f"   [{m['doc_type']}/{m['product_area']}] {m['title']}")

    print("\n" + "-" * 80 + "\n")
    print(result.answer)
    print("\n" + "-" * 80 + "\n")
    print("Thank you for using the MegaWasher RAG app! Have an awesome day :) ")


if __name__ == "__main__":
    main()

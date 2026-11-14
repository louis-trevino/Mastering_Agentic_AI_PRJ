"""Interactive SuperGlasses hybrid RAG command-line application."""

from __future__ import annotations

from rag_service import ConfigurationError, get_rag_service


def print_sources(service: object, question: str) -> None:
    """Print citations for a question using the shared retrieval service."""
    documents = service.retrieve(question)
    print("\nCitations:")
    for document in documents:
        metadata = document.metadata
        print(
            f"   [{metadata.get('doc_type', 'unknown')}/"
            f"{metadata.get('category', 'unknown')}] "
            f"{metadata.get('title', 'Untitled source')}"
        )


def main() -> None:
    """Run the interactive terminal workflow."""
    try:
        service = get_rag_service()
    except (ConfigurationError, KeyError) as exc:
        print(f"Unable to start SuperGlasses RAG: {exc}")
        return

    print("\n*** Welcome to SuperGlasses FAQ Tool ***")
    user_query = input("\nQuery: ").strip()
    if not user_query:
        print("Please enter a question.")
        return

    try:
        print_sources(service, user_query)
        result = service.search(user_query)
    except Exception as exc:
        print(f"\nThe search could not be completed: {exc}")
        return

    print("\n" + "-" * 80 + "\n")
    print(result.answer)
    print("\n" + "-" * 80 + "\n")
    print(
        "Thank you for using the SuperGlasses RAG app! "
        "Have an awesome day :) \n"
    )


if __name__ == "__main__":
    main()

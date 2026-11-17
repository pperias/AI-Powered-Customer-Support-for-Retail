from ..types import Passage


def retrieve(query: str, product_id: str | None = None, k: int = 4) -> list[Passage]:
    """Return the most relevant passages from product manuals and policy documents.

    CONTRACT: keep this signature. The RAG owner replaces the body (chunking, embeddings,
    vector store, ranking) and puts the source documents in data/docs/.
    """
    return []  # TODO(RAG owner)

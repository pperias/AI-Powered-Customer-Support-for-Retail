from ..rag import retrieve
from ..session import Session
from ..types import Reply


def answer(session: Session, message: str) -> Reply:
    """Answer product questions from retrieved documents. The customer can ask many in a row.

    TODO(Priya): have the LLM write the answer from the passages, citing the source, and
    record what was covered in session.topics_covered.
    """
    passages = retrieve(message, product_id=session.product_id)
    if not passages:
        return Reply("(RAG is not connected yet, so I cannot answer product questions.)")
    return Reply(passages[0].text)

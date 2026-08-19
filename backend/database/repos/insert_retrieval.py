from datetime import datetime, timezone
from uuid import UUID

from database.models.retrieval_table import RetrievalTable
from database.session import SessionLocal


def insert_retrieval(
        execution_id: UUID,
        pass_number: str,
        sufficient: bool,
        confidence: float,
        reasoning: str,
        refined_query: str = "No Refined Query",
        selected_chunks: list = None
    ):
    db = SessionLocal()

    try:
        record = RetrievalTable(
            execution_id=execution_id,
            pass_number=pass_number,
            sufficient=sufficient,
            confidence=confidence,
            reasoning=reasoning,
            refined_query=refined_query,
            selected_chunks=selected_chunks
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    finally:
        db.close()
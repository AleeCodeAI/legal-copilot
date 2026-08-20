from uuid import UUID

from database.models.synthesis_table import SynthesisTable
from database.session import SessionLocal


def insert_synthesis(
        execution_id: UUID,
        answer: str = "No Answer",
        reasoning_summary: str = "No Reasoning",
        citations: list[dict] = None
    ):
    db = SessionLocal()

    try:
        record = SynthesisTable(
            execution_id=execution_id,
            answer=answer,
            reasoning_summary=reasoning_summary,
            citations=citations
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    finally:
        db.close()
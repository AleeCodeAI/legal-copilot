from uuid import UUID

from database.models.history_table import HistoryTable
from database.session import SessionLocal


def insert_history(
        history_id: UUID,
        query: str,
        answer: str,
        citations: list[dict]
    ):
    db = SessionLocal()

    try:
        record = HistoryTable(
            history_id = history_id,
            query = query,
            answer = answer,
            citations = citations
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    finally:
        db.close()



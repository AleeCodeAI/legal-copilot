from datetime import datetime, timezone
from uuid import UUID

from database.models.execution_table import ExecutionTable
from database.session import SessionLocal


def insert_execution(
        execution_id: UUID,
        query: str,
    ):
    db = SessionLocal()

    try:
        record = ExecutionTable(
            execution_id=execution_id,
            query=query,
            status=False,
            created_at=datetime.now(timezone.utc),
            error_message="No error",
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    finally:
        db.close()


def mark_execution_success(execution_id: UUID):
    db = SessionLocal()

    try:
        db.query(ExecutionTable).filter(
            ExecutionTable.execution_id == execution_id
        ).update(
            {
                "status": True,
                "completed_at": datetime.now(timezone.utc),
            }
        )

        db.commit()

    finally:
        db.close()


def mark_execution_failure(
    execution_id: UUID,
    error_message: str,
):
    db = SessionLocal()

    try:
        db.query(ExecutionTable).filter(
            ExecutionTable.execution_id == execution_id
        ).update(
            {
                "status": False,
                "completed_at": datetime.now(timezone.utc),
                "error_message": error_message,
            }
        )

        db.commit()

    finally:
        db.close()
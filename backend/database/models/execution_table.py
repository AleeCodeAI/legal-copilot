from sqlalchemy import Column, String, UUID, DateTime, Text
from database.base import Base


class ExecutionTable(Base):
    __tablename__ = "execution_table"

    # Same ID used as the Langfuse session_id
    execution_id = Column(UUID, primary_key=True, nullable=False)

    query = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    error_message = Column(Text, nullable=True) # Filled if anything breaks